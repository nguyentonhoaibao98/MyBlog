import {env} from 'cloudflare:workers';
import {getDb} from '../../../db';
import {topics,attempts} from '../../../db/schema';
import {eq} from 'drizzle-orm';
export const dynamic='force-dynamic';
const secret=()=>String((env as any).ADMIN_CODE||'');
async function signature(value:string){const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret()),{name:'HMAC',hash:'SHA-256'},false,['sign']);return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(value)))).map(v=>v.toString(16).padStart(2,'0')).join('');}
async function admin(r:Request){if(!secret())return false;const token=r.headers.get('cookie')?.match(/(?:^|; )bc_session=([^;]+)/)?.[1];if(!token)return false;const [expires,sig]=token.split('.');return Number(expires)>Date.now()&&sig===await signature(expires);}
function json(data:any,status=200,headers={}){return Response.json(data,{status,headers:{'Cache-Control':'no-store',...headers}})}
async function handle(r:Request){try{
 const path=new URL(r.url).pathname,db=getDb(),isAdmin=await admin(r);
 if(r.method!=='GET'&&r.headers.get('origin')!==new URL(r.url).origin)return json({error:'Invalid request.'},403);
 if(path==='/api/session'&&r.method==='GET')return json({admin:isAdmin});
 if(path==='/api/logout'&&r.method==='POST')return json({ok:true},200,{'Set-Cookie':'bc_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0'});
 if(path==='/api/login'&&r.method==='POST'){
 const ip=r.headers.get('cf-connecting-ip')||'local',id=await signature(ip),now=Date.now();const [a]=await db.select().from(attempts).where(eq(attempts.id,id));if(a&&a.until>now&&a.count>=8)return json({error:'Too many attempts. Please try again in 15 minutes.'},429);
 const {code}=await r.json() as any;if(!secret()||typeof code!=='string'||code!==secret()){const data={count:a&&a.until>now?a.count+1:1,until:a&&a.until>now?a.until:now+900000};await db.insert(attempts).values({id,...data}).onConflictDoUpdate({target:attempts.id,set:data});return json({error:'Incorrect access code. Please try again.'},401)}
 await db.delete(attempts).where(eq(attempts.id,id));const exp=String(now+28800000);return json({ok:true},200,{'Set-Cookie':'bc_session='+exp+'.'+await signature(exp)+'; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=28800'});
 }
 if(path==='/api/topics'&&r.method==='GET'){const rows=isAdmin?await db.select().from(topics):await db.select().from(topics).where(eq(topics.public,1));return json(rows.sort((a,b)=>b.created.localeCompare(a.created)))}
 if(path.startsWith('/api/file/')&&r.method==='GET'){const id=path.split('/').pop()!;const [t]=await db.select().from(topics).where(eq(topics.id,id));if(!t||(!t.public&&!isAdmin)||!t.file)return json({error:'Document not found.'},404);const f=await (env as any).BUCKET.get(t.file);if(!f)return json({error:'File not found.'},404);return new Response(f.body,{headers:{'Content-Type':'application/pdf','Content-Disposition':"inline; filename*=UTF-8''"+encodeURIComponent(t.filename||'document.pdf'),'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}})}
 if(!isAdmin)return json({error:'Please sign in as Admin.'},401);
 if(path==='/api/topics'&&r.method==='POST'){
 const form=await r.formData(),title=String(form.get('title')||'').trim();if(!title||title.length>200)return json({error:'Title must be between 1 and 200 characters.'},400);
 const f=form.get('pdf');if(!(f instanceof File)||f.size>20*1024*1024||f.size<5)return json({error:'Please select a PDF up to 20 MB.'},400);if(new TextDecoder().decode(await f.slice(0,5).arrayBuffer())!=='%PDF-')return json({error:'The file is not a valid PDF.'},400);
 const id=crypto.randomUUID(),key='pdf/'+id+'.pdf';await (env as any).BUCKET.put(key,f.stream(),{httpMetadata:{contentType:'application/pdf'}});
 const row={id,title,summary:String(form.get('summary')||'').slice(0,2000),category:String(form.get('category')||'Business Central').slice(0,100),content:String(form.get('content')||'').slice(0,100000),public:form.get('public')==='true'?1:0,file:key,filename:f.name,created:new Date().toISOString()};try{await db.insert(topics).values(row)}catch(e){await (env as any).BUCKET.delete(key);throw e}return json(row,201);
 }
 if(path.startsWith('/api/topics/')&&r.method==='PATCH'){const id=path.split('/').pop()!,b=await r.json() as any;const [old]=await db.select().from(topics).where(eq(topics.id,id));if(!old)return json({error:'Article not found.'},404);const data={title:String(b.title||old.title).slice(0,200),summary:String(b.summary??old.summary).slice(0,2000),category:String(b.category||old.category).slice(0,100),content:String(b.content??old.content).slice(0,100000),public:b.public===undefined?old.public:b.public?1:0};await db.update(topics).set(data).where(eq(topics.id,id));return json({...old,...data})}
 if(path.startsWith('/api/topics/')&&r.method==='DELETE'){const id=path.split('/').pop()!;const [t]=await db.select().from(topics).where(eq(topics.id,id));if(!t)return json({error:'Article not found.'},404);await db.delete(topics).where(eq(topics.id,id));if(t.file)await (env as any).BUCKET.delete(t.file);return json({ok:true})}
 return json({error:'Not found.'},404);
 }catch(e){console.error(e);return json({error:'Unable to process your request. Please try again.'},500)}}
export const GET=handle,POST=handle,PATCH=handle,DELETE=handle;

