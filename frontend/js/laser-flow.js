/* Vanilla adaptation of React Bits LaserFlow: decorative only, no framework dependency. */
(function () {
  const VERTEX = 'attribute vec2 p; void main(){gl_Position=vec4(p,0.0,1.0);}';
  const FRAGMENT = `precision mediump float;
uniform vec2 uSize; uniform float uTime; uniform vec2 uMouse; uniform vec3 uColor;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+vec2(1.,1.)),f.x),f.y);}
float fbm(vec2 p){float v=0.;for(int i=0;i<4;i++){v+=noise(p)*.5;p=p*2.02+7.;}return v;}
void main(){vec2 uv=(gl_FragCoord.xy-.5*uSize)/min(uSize.x,uSize.y);float t=uTime*.35;float tilt=(uMouse.x-.5)*.08;uv.x-=tilt*(uv.y+0.35);float beam=exp(-abs(uv.y+0.12*sin(uv.x*3.0+t*.8))*(17.0+5.0*sin(t)));float core=exp(-abs(uv.y)*75.);float fog=fbm(uv*2.2+vec2(t*.08,-t*.1))*.42*exp(-length(uv)*1.3);float wisps=step(.72,fract((uv.x*3.0+uv.y*8.0-t*1.8)+noise(uv*4.)));wisps*=beam*.22;float edge=smoothstep(1.35,.15,length(uv));float a=(beam*.42+core*.22+fog+wisps)*edge;gl_FragColor=vec4(uColor*a,a*.72);}`;
  function color(hex) { let c=(hex||'#38bdf8').replace('#',''); if(c.length===3)c=c.split('').map(x=>x+x).join(''); const n=parseInt(c,16)||0x38bdf8; return [((n>>16)&255)/255,((n>>8)&255)/255,(n&255)/255]; }
  function initLaserFlow(container, options) {
    if (!container) return () => {};
    if (container.__laserFlowCleanup) return container.__laserFlowCleanup;
    const opts=Object.assign({color:'#38bdf8', dpr:1.25},options||{}); const canvas=document.createElement('canvas'); canvas.className='laser-flow-canvas'; container.appendChild(canvas);
    let gl=null, program=null, raf=0, ro=null, start=performance.now(), mouse=[.5,.5], disposed=false;
    try {
      gl=canvas.getContext('webgl',{alpha:true,antialias:false,powerPreference:'low-power'}); if(!gl) throw new Error('WebGL unavailable');
      const compile=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
      program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,VERTEX));gl.attachShader(program,compile(gl.FRAGMENT_SHADER,FRAGMENT));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('LaserFlow program link failed');gl.useProgram(program);
      const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);const loc=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
      const timeLoc=gl.getUniformLocation(program,'uTime'),sizeLoc=gl.getUniformLocation(program,'uSize'),mouseLoc=gl.getUniformLocation(program,'uMouse'),colorLoc=gl.getUniformLocation(program,'uColor'),rgb=color(opts.color);
      const resize=()=>{const r=container.getBoundingClientRect(),d=Math.min(opts.dpr,window.devicePixelRatio||1);canvas.width=Math.max(1,Math.floor(r.width*d));canvas.height=Math.max(1,Math.floor(r.height*d));canvas.style.width=r.width+'px';canvas.style.height=r.height+'px';gl.viewport(0,0,canvas.width,canvas.height);};
      const move=e=>{const r=container.getBoundingClientRect();mouse=[(e.clientX-r.left)/Math.max(r.width,1),1-(e.clientY-r.top)/Math.max(r.height,1)];};
      const frame=now=>{if(disposed)return;raf=requestAnimationFrame(frame);if(document.hidden)return;gl.uniform1f(timeLoc,(now-start)/1000);gl.uniform2f(sizeLoc,canvas.width,canvas.height);gl.uniform2f(mouseLoc,mouse[0],mouse[1]);gl.uniform3f(colorLoc,rgb[0],rgb[1],rgb[2]);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.drawArrays(gl.TRIANGLES,0,3);};
      container.addEventListener('pointermove',move,{passive:true});window.addEventListener('resize',resize,{passive:true});ro=new ResizeObserver(resize);ro.observe(container);resize();frame(performance.now());
      const cleanup=()=>{if(disposed)return;disposed=true;cancelAnimationFrame(raf);ro&&ro.disconnect();container.removeEventListener('pointermove',move);window.removeEventListener('resize',resize);gl.deleteProgram(program);canvas.remove();container.__laserFlowCleanup=null;};
      container.__laserFlowCleanup=cleanup;
      return cleanup;
    } catch (e) { console.warn('LaserFlow disabled:',e.message); canvas.remove(); container.classList.add('laser-flow-fallback'); return ()=>{disposed=true;cancelAnimationFrame(raf);}; }
  }
  window.initLaserFlow=initLaserFlow;
  function bootstrap() {
    const container=document.getElementById('laserFlowBackground');
    if (!container) return;
    const cleanup=initLaserFlow(container,{color:'#38bdf8',dpr:1.25});
    window.addEventListener('pagehide',cleanup,{once:true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',bootstrap,{once:true});
  else bootstrap();
})();
