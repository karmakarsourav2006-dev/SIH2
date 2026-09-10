import sys
import unittest
import json
import httpx

from backend.config import settings
from backend.llm.ollama_client import OllamaClient
from backend.services.ai_tools import AITools
from backend.rag.research_rag import ResearchRAG
from backend.llm.conversation_manager import ConversationManager
from backend.services.emergency import EmergencySupervisor
from backend.services.digital_twin import DigitalTwin

class PolarAITestSuite(unittest.TestCase):

    def test_01_ollama_connection(self):
        """Test Ollama daemon connection and model availability."""
        health = OllamaClient.check_health()
        print("\n[TEST 1] Ollama Health:", health)
        self.assertEqual(health.get("status"), "online")
        self.assertIn("llama3.2:latest", health.get("available_models", []))

    def test_02_rag_indexing_and_retrieval(self):
        """Test Research RAG indexing and similarity retrieval."""
        count = ResearchRAG.index_documents()
        print(f"\n[TEST 2] RAG Index Chunks: {count}")
        self.assertGreater(count, 0)
        
        # Query battery literature
        results = ResearchRAG.retrieve("LiFePO4 battery sub-zero impedance", top_k=2)
        self.assertGreater(len(results), 0)
        print(f"[TEST 2] RAG Retrieved {len(results)} chunks. Top score: {results[0]['score']}")
        self.assertIn("source", results[0])

    def test_03_tool_calling_live_data(self):
        """Test all 16 backend tools against live project state."""
        print("\n[TEST 3] Testing Backend AI Tools:")
        status = AITools.get_station_status("ST-01")
        self.assertIn("battery_kwh", status)
        self.assertEqual(status["station_id"], "ST-01")

        sched = AITools.get_current_schedule("ST-01")
        self.assertIsInstance(sched, list)
        self.assertGreater(len(sched), 0)

        act_name = sched[0]["name"]
        energy = AITools.get_activity_energy(act_name, "ST-01")
        power = AITools.get_activity_power(act_name, "ST-01")
        self.assertIn("required_kwh", energy)
        self.assertIn("continuous_power_kw", power)

        forecast = AITools.get_energy_forecast("ST-01", hours=12)
        self.assertIn("timeline", forecast)

        weather = AITools.get_weather_forecast("ST-01")
        self.assertIn("temp_c", weather)

        heat = AITools.get_heating_forecast("ST-01")
        self.assertIn("estimated_heating_kw", heat)

        batt = AITools.get_battery_status("ST-01")
        self.assertIn("soc_pct", batt)

        alerts = AITools.get_alerts("ST-01")
        self.assertIsInstance(alerts, list)

        anomalies = AITools.get_anomalies("ST-01")
        self.assertIsInstance(anomalies, list)
        print(" -> Verified status, schedule, energy, power, forecasts, battery, alerts, anomalies.")

    def test_04_simulation_what_if(self):
        """Test non-destructive what-if activity simulation."""
        sim = AITools.simulate_activity("ST-01", "High-Power Ice Radar", 30.0, 3.0)
        print("\n[TEST 4] Simulation Output:", sim)
        self.assertEqual(sim["simulation_mode"], "WHAT_IF_NON_DESTRUCTIVE")
        self.assertIn("projected_safe_runway_hours", sim)

    def test_05_activity_crud_actions(self):
        """Test creating, updating, rescheduling, and deleting activities in database."""
        # Create
        created = AITools.create_activity("ST-01", "Deep Seismic Survey", 18.0, 2.0, 24.0, 2)
        act_id = created["activity_id"]
        self.assertTrue(created["ok"])
        print(f"\n[TEST 5] Created Activity: {act_id}")

        # Update
        updated = AITools.update_activity(act_id, required_kwh=22.0)
        self.assertTrue(updated["ok"])

        # Reschedule
        rescheduled = AITools.reschedule_activity(act_id, "SLOT_0800_1000")
        self.assertTrue(rescheduled["ok"])

        # Delete
        deleted = AITools.delete_activity(act_id)
        self.assertTrue(deleted["ok"])
        print(" -> Activity lifecycle (Create -> Update -> Reschedule -> Delete) completed cleanly.")

    def test_06_conversation_memory_and_anaphora(self):
        """Test multi-turn context awareness and pronoun resolution."""
        session_id = "test_memory_suite_99"
        
        # Turn 1: schedule inquiry
        t1 = ConversationManager.handle_query("Show me the current station schedule", session_id=session_id)
        self.assertEqual(t1["intent"], "GET_SCHEDULE")

        # Turn 2: calculation on "it"
        t2 = ConversationManager.handle_query("How much energy would it require?", session_id=session_id)
        print("\n[TEST 6 Turn 2] Resolved Query:", t2["resolved_query"])
        self.assertEqual(t2["intent"], "GET_ACTIVITY_ENERGY")
        session = ConversationManager.get_session(session_id)
        self.assertIn(session.last_activity_name, t2["resolved_query"])

        # Turn 3: simulation on "this" tomorrow
        t3 = ConversationManager.handle_query("What if we add this tomorrow for 2 hours?", session_id=session_id)
        print("[TEST 6 Turn 3] Resolved Query:", t3["resolved_query"])
        self.assertEqual(t3["intent"], "SIMULATE_SCENARIO")
        self.assertIn(session.last_activity_name, t3["resolved_query"])
        self.assertIn("tomorrow", t3["resolved_query"])



    def test_07_deterministic_emergency_and_voice_alert(self):
        """Test 4-tier emergency evaluation and automatic voice alarms."""
        # Simulated Code Red Emergency (SoC = 12%, negative flow)
        audit = EmergencySupervisor.audit_station_safety(
            station_id="ST-01",
            battery_kwh=19.2,
            battery_capacity_kwh=160.0,
            total_gen_kw=5.0,
            total_renewables_kw=5.0,
            active_demand_kw=25.0,
            gen_kw=0.0,
            wind_mps=12.0
        )
        print("\n[TEST 7] Emergency Audit Result:")
        print(" Severity:", audit["severity"])
        print(" Mode:", audit["mode"])
        print(" Voice Alert:", audit["auto_voice_alert"])
        self.assertEqual(audit["severity"], "EMERGENCY")
        self.assertEqual(audit["mode"], "SURVIVAL CRITICAL")
        self.assertIsNotNone(audit["auto_voice_alert"])
        # Verify non-critical loads shed
        p2_p3_online = [l for l in audit["loads"] if l["priority"] in (2, 3) and l["status"] == "ONLINE"]
        self.assertEqual(len(p2_p3_online), 0)

    def test_08_llm_fallback_when_unreachable(self):
        """Test system behavior when Ollama endpoint is temporarily unreachable."""
        # Call handle_query with invalid port override to test graceful fallback
        old_url = settings.OLLAMA_URL
        settings.OLLAMA_URL = "http://127.0.0.1:9999" # invalid port
        try:
            res = ConversationManager.handle_query("What is our current energy status?", session_id="fb_sess")
            print("\n[TEST 8] Fallback Response Provider:", res["provider"])
            self.assertEqual(res["provider"], "Deterministic Rule Supervisor")
            self.assertTrue(len(res["explanation"]) > 0)
        finally:
            settings.OLLAMA_URL = old_url

if __name__ == "__main__":
    unittest.main(verbosity=2)
