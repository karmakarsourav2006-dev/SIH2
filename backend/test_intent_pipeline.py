import sys
import unittest
import json
from backend.llm.conversation_manager import ConversationManager
from backend.llm.intent_classifier import IntentClassifier

class TestIntentPipeline(unittest.TestCase):
    def test_single_turn_intents(self):
        cases = [
            ("Tell me about yourself.", "GENERAL_CONVERSATION", None),
            ("How much energy do we have?", "GET_CURRENT_ENERGY", "get_current_energy"),
            ("Tell me about the schedule.", "GET_SCHEDULE", "get_current_schedule"),
            ("Can I change the schedule?", "SCHEDULE_MODIFICATION_POLICY", None),
            ("What is the weather?", "GET_WEATHER", "get_weather_forecast"),
            ("What can you do?", "GENERAL_CONVERSATION", None),
            ("What is the battery level?", "GET_BATTERY_STATUS", "get_battery_status"),
        ]
        session = {"recent_turns": [], "last_activity_mentioned": None}
        for query, expected_intent, expected_tool in cases:
            res = IntentClassifier.classify(query, session)
            self.assertEqual(res["intent"], expected_intent, f"Query '{query}' classified as {res['intent']}, expected {expected_intent}")
            self.assertEqual(res["selected_tool"], expected_tool, f"Query '{query}' selected tool {res['selected_tool']}, expected {expected_tool}")

    def test_sequential_multi_turn_execution(self):
        session_id = "test_suite_consecutive"
        
        # 1. 'Tell me about yourself.' -> GENERAL_CONVERSATION, zero telemetry
        res1 = ConversationManager.handle_query("Tell me about yourself.", session_id=session_id)
        self.assertEqual(res1["intent"], "GENERAL_CONVERSATION")
        self.assertNotIn("53.", res1["explanation"])

        # 2. 'How much energy do we have?' -> GET_CURRENT_ENERGY
        res2 = ConversationManager.handle_query("How much energy do we have?", session_id=session_id)
        self.assertEqual(res2["intent"], "GET_CURRENT_ENERGY")
        self.assertIn("stored_energy_kwh", res2["tool_results"])
        self.assertTrue("kwh" in res2["explanation"].lower() or "battery" in res2["explanation"].lower() or "energy" in res2["explanation"].lower())

        # 3. 'Tell me about the schedule.' -> GET_SCHEDULE
        res3 = ConversationManager.handle_query("Tell me about the schedule.", session_id=session_id)
        self.assertEqual(res3["intent"], "GET_SCHEDULE")
        self.assertTrue(isinstance(res3["tool_results"], list) and len(res3["tool_results"]) > 0)

        # 4. 'Can I change the schedule?' -> SCHEDULE_MODIFICATION_POLICY
        res4 = ConversationManager.handle_query("Can I change the schedule?", session_id=session_id)
        self.assertEqual(res4["intent"], "SCHEDULE_MODIFICATION_POLICY")
        self.assertTrue("schedule" in res4["explanation"].lower() or "policy" in res4["explanation"].lower() or "permission" in res4["explanation"].lower() or "supervisor" in res4["explanation"].lower())

        # 5. 'What is the weather?' -> GET_WEATHER
        res5 = ConversationManager.handle_query("What is the weather?", session_id=session_id)
        self.assertEqual(res5["intent"], "GET_WEATHER")
        self.assertIn("wind_mps", res5["tool_results"])

        # 6. 'What can you do?' -> GENERAL_CONVERSATION
        res6 = ConversationManager.handle_query("What can you do?", session_id=session_id)
        self.assertEqual(res6["intent"], "GENERAL_CONVERSATION")
        self.assertNotIn("battery_kwh", res6.get("tool_results", {}))

        # 7. 'What is the battery level?' -> GET_BATTERY_STATUS
        res7 = ConversationManager.handle_query("What is the battery level?", session_id=session_id)
        self.assertEqual(res7["intent"], "GET_BATTERY_STATUS")
        self.assertIn("state_of_charge_pct", res7["tool_results"])

if __name__ == "__main__":
    unittest.main()

