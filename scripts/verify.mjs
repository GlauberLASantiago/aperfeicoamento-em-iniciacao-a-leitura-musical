import assert from 'node:assert/strict';import {readFile,readdir,stat} from 'node:fs/promises';import {createHash} from 'node:crypto';import path from 'node:path';import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const db=JSON.parse(await readFile(path.join(root,'course.json'),'utf8')),manifest=JSON.parse(await readFile(path.join(root,'docs/file-integrity.json'),'utf8'));
assert.equal(Object.keys(db.activities).length,179);assert.equal(Object.keys(db.questions).length,103);assert.equal(db.localVideos.length,9);assert.equal(db.missingFiles.length,40);
const linked=new Set(db.sections.flatMap(s=>s.activityIds));
for(const [id,a] of Object.entries(db.activities)){assert(linked.has(id),'Activity outside section: '+id);if(a.type==='quiz')for(const qid of a.questionIds)assert(db.questions[qid],'Missing question '+qid);}
for(const file of manifest){const blob=await readFile(path.join(root,file.url));assert.equal(blob.length,file.bytes,file.url);assert.equal(createHash('sha256').update(blob).digest('hex'),file.sha256,file.url);assert.equal(createHash('sha1').update(blob).digest('hex'),file.sha1,file.url);}
assert.deepEqual(new Set((await readdir(path.join(root,'files'))).map(p=>'files/'+p)),new Set(manifest.map(f=>f.url)),'Unexpected published file');
let localLinks=0;const fragments=[];
for(const a of Object.values(db.activities))fragments.push(a.intro,a.html||'',...a.chapters.map(c=>c.html));
for(const q of Object.values(db.questions))fragments.push(q.html,q.feedback,...q.answers.flatMap(a=>[a.html,a.feedback]));
for(const fragment of fragments){assert(!/@@PLUGINFILE@@|<script\b|\son\w+\s*=|javascript:|<form\b/i.test(fragment),'Unsafe or unresolved active HTML');for(const match of fragment.matchAll(/(?:src|href)="(files\/[^"]+)"/g)){assert(manifest.some(f=>f.url===match[1]),'Missing local resource: '+match[1]);localLinks++;}for(const match of fragment.matchAll(/href="#atividade-([^"/]+)(?:\/capitulo-[^"]+)?"/g))assert(db.activities[match[1]],'Invalid activity link '+match[1]);}
for(const v of db.localVideos){assert(manifest.some(f=>f.url===v.playUrl));assert(manifest.some(f=>f.url===v.originalUrl));}
console.log('PASS: 179 resources/activities, 103 questions, '+manifest.length+' byte-verified files, '+localLinks+' local HTML links, nine converted videos and 40 explicitly missing files.');
