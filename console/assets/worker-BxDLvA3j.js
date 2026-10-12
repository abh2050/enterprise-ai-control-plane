let e=null,t=null;const n=e=>self.postMessage(e);async function r(e){let t=await crypto.subtle.digest(`SHA-256`,e);return[...new Uint8Array(t)].map(e=>e.toString(16).padStart(2,`0`)).join(``)}async function i(i,a){let o=performance.now();n({type:`progress`,step:`Loading Python`});let s=`${i}pyodide/`,{loadPyodide:c}=await import(
/* @vite-ignore */
`${s}pyodide.mjs`);t=await c({indexURL:s,lockFileURL:`${s}pyodide-lock.json`,stdout:()=>{},stderr:()=>{}}),n({type:`progress`,step:`Loading packages`});let l=await(await fetch(`${s}packages.json`)).json();await t.loadPackage(l,{messageCallback:()=>{}}),n({type:`progress`,step:`Loading the backend`});let u=await(await fetch(`${i}manifest.json`)).json(),d=await(await fetch(`${i}${u.bundle}`)).arrayBuffer();if(await r(d)!==u.sha256)throw Error(`backend bundle failed its integrity check`);t.unpackArchive(d,`zip`,{extractDir:`/app`}),t.globals.set(`demo_env`,t.toPy({BIND_HOST:`browser`,IDENTITY_MODE:`fixture`,STORE_BACKEND:`memory`,PROVIDER_MODE:`fixture`,FIXED_NOW:a})),await t.runPythonAsync(`
import os, sys
sys.path.insert(0, "/app/backend")
os.chdir("/app")
os.environ.update(demo_env)
from control_plane.api import create_app
from control_plane.browser import Bridge
bridge = Bridge(create_app())
`),n({type:`progress`,step:`Seeding the registry`}),e=t.globals.get(`bridge`),await e.start(),n({type:`ready`,ms:Math.round(performance.now()-o)})}let a=Promise.resolve();self.onmessage=r=>{let o=r.data;o.type===`boot`?i(o.base,o.fixedNow).catch(e=>n({type:`failed`,error:String(e)})):a=a.then(async()=>{try{if(!e||!t)throw Error(`engine not ready`);let r=await e.request_json(o.method,o.path,t.toPy(o.headers),o.body),i=JSON.parse(r);n({type:`response`,id:o.id,status:i.status,body:i.body})}catch(e){n({type:`response`,id:o.id,status:500,body:JSON.stringify({detail:String(e)})})}})};