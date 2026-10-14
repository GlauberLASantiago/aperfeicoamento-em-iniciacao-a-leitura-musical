const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const plain=s=>String(s||'').replace(/<[^>]*>/g,' ').replace(/&nbsp;/g,' ').replace(/\s+/g,' ').trim();
const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const types={book:'Livro e aulas',page:'Material de estudo',assign:'Atividade',quiz:'Questionário para estudo',forum:'Orientações de fórum',chat:'Orientações de interação',resource:'Arquivo ou material',url:'Referência',label:'Orientação'};
let db,active='',libraryFilter='';
const bytes=n=>n>1e6?(n/1e6).toFixed(1)+' MB':Math.max(1,Math.round(n/1000))+' KB';
const primarySections=()=>db.sections.filter(s=>s.source!=='secondary');
const sectionOf=id=>db.sections.find(s=>s.activityIds.includes(id));
const link=(id,label,cls='')=>'<a class="'+cls+'" href="#atividade-'+esc(id)+'">'+esc(label)+'</a>';
function nav(){
  const main=primarySections(),old=db.sections.filter(s=>s.source==='secondary');
  $('navigation').innerHTML='<a href="#inicio">Visão geral</a><a href="#biblioteca">Biblioteca de arquivos</a><a href="#videos">Vídeos locais</a><a href="#questoes">Banco de questões</a><p class="nav-label">PERCURSO DO CURSO</p>'+
  main.map(s=>'<details data-section="'+esc(s.id)+'"><summary>'+esc(s.name==='Oculto'?'Materiais complementares':s.name)+'</summary><a href="#secao-'+esc(s.id)+'">Visão da seção →</a>'+s.activityIds.map(id=>db.activities[id]).filter(a=>a.type!=='label').map(a=>link(a.id,a.name)).join('')+'</details>').join('')+
  '<p class="nav-label">OUTRA VERSÃO RECUPERADA</p><details><summary>Versão anterior do curso</summary>'+old.filter(s=>s.activityIds.length).map(s=>'<a href="#secao-'+esc(s.id)+'">'+esc(s.name)+'</a>').join('')+'</details><p class="nav-label">SOBRE ESTE ACERVO</p><a href="#sobre">Sobre o resgate</a>';
}
function home(){
  const units=primarySections().filter(s=>/^Unidade \d/.test(s.name));
  return '<section class="hero"><p class="eyebrow">ACERVO RECUPERADO · EDUCAÇÃO MUSICAL</p><h1>'+esc(db.title)+'</h1><p class="lead">Aulas, partituras, áudios e atividades reunidos para retomar os estudos de leitura musical. A organização e os conteúdos do curso original foram preservados.</p><a class="primary" href="#secao-'+units[0].id+'">Começar pela Unidade 1 →</a><a class="secondary" href="#biblioteca">Explorar os arquivos</a><div class="stats"><div><strong>'+units.length+'</strong><span>unidades do curso</span></div><div><strong>25</strong><span>livros resgatados em duas versões</span></div><div><strong>'+db.localVideos.length+'</strong><span>vídeos locais</span></div></div></section><p class="eyebrow">PERCURSO DE ESTUDO</p><div class="unit-grid">'+units.map((s,i)=>'<a class="unit-card" href="#secao-'+esc(s.id)+'"><span class="unit-no">LEITURA MUSICAL · '+String(i+1).padStart(2,'0')+'</span><h3>'+esc(s.name)+'</h3><p>'+s.activityIds.map(id=>db.activities[id]).filter(a=>a.type!=='label').length+' materiais e atividades →</p></a>').join('')+'</div><h2>Retomar o curso</h2><p class="lead">Consulte as orientações de apresentação e o guia da disciplina. Os questionários reúnem os enunciados, alternativas e comentários preservados para estudo independente.</p><div class="resource-list">'+link('102428','Guia da Disciplina','resource')+link('102429','Apresentação e organização original','resource')+'<a class="resource" href="#sobre">Conhecer o resgate e os materiais ausentes →</a></div>';
}
function sectionView(s){
  const name=s.name==='Oculto'?'Materiais complementares':s.name;
  return '<p class="breadcrumb"><a href="#inicio">Acervo</a> / '+esc(name)+'</p><p class="eyebrow">'+(s.source==='secondary'?'VERSÃO ANTERIOR RECUPERADA':'PERCURSO DO CURSO')+'</p><h1>'+esc(name)+'</h1><div class="prose">'+s.html+'</div><div class="resource-list">'+s.activityIds.map(id=>{
    const a=db.activities[id];
    if(a.type==='label')return '<div class="separator"><div class="prose">'+a.intro+'</div></div>';
    return '<a class="resource" href="#atividade-'+esc(id)+'"><div><strong>'+esc(a.name)+'</strong><small>'+esc(types[a.type]||a.type)+(a.hidden?' · material originalmente oculto':'')+'</small></div><span class="arrow" aria-hidden="true">→</span></a>';
  }).join('')+'</div>';
}
function attachments(a){
  if(!a.files?.length)return '';
  return '<section class="downloads"><h2>Arquivos desta atividade</h2><ul>'+a.files.map(f=>'<li>'+(f.available?'<a href="'+esc(f.url)+'" download="'+esc(f.filename)+'">'+esc(f.filename)+'</a> <small>'+bytes(f.size)+'</small>':'<span class="unavailable">'+esc(f.filename)+' · não incluído no backup</span>')+'</li>').join('')+'</ul></section>';
}
function question(q,index){
  const answers=q.answers||[],self=q.selfAssessment||q.name.includes('_resp');
  const options=answers.length?'<div class="choices">'+answers.map((a,i)=>'<label class="choice"><input type="radio" name="q-'+esc(q.id)+'"><span class="choice-letter">'+String.fromCharCode(65+i)+'</span><div class="prose">'+a.html+'</div></label>').join('')+'</div>':'';
  const marked=answers.filter(a=>a.fraction>0);
  const feedback=(self?answers:marked).map(a=>'<div class="answer-line"><strong>'+(self?'Critério preservado':'Alternativa '+String.fromCharCode(65+answers.indexOf(a)))+'</strong><div class="prose">'+a.html+a.feedback+'</div></div>').join('');
  const details=(feedback||q.feedback)?'<details class="answer"><summary>'+(self?'Ver critérios de autoavaliação':'Ver gabarito e comentários')+'</summary><div class="answer-body">'+feedback+'<div class="prose">'+q.feedback+'</div></div></details>':'';
  const warning=q.unavailableFiles?.length?'<p class="note missing-note">As mídias desta questão não vieram nos backups. O enunciado e as alternativas textuais estão preservados.</p>':'';
  const heading=q.type==='description'?'Enunciado original':(self?'Autoavaliação · questão ':'Questão ')+(index+1);
  const body=self?'<details class="answer"><summary>Ver partitura e critérios de autoavaliação</summary><div class="answer-body"><div class="prose">'+q.html+'</div>'+options+'<div class="prose">'+q.feedback+'</div></div></details>':'<div class="prose">'+q.html+'</div>'+options+details;
  return '<section class="question" id="questao-'+esc(q.id)+'"><h2>'+heading+'</h2>'+warning+body+'</section>';
}
function activity(a,chapter){
  const section=sectionOf(a.id),unit=section?.name==='Oculto'?'Materiais complementares':section?.name;
  let body='<p class="breadcrumb"><a href="#inicio">Acervo</a> / '+(section?'<a href="#secao-'+esc(section.id)+'">'+esc(unit)+'</a>':'Material')+'</p><span class="tag">'+esc(types[a.type]||'Material')+'</span>'+(a.source==='secondary'?'<span class="tag">Versão anterior</span>':'')+'<h1>'+esc(a.name)+'</h1>';
  if(['assign','quiz'].includes(a.type))body+='<p class="note">Atividade recuperada para estudo independente. As orientações originais estão reproduzidas abaixo.</p>';
  body+='<div class="prose">'+a.intro+(a.html||'')+'</div>';
  if(a.chapters.length)body+='<nav class="chapter-index" aria-label="Capítulos">'+a.chapters.map(c=>'<a href="#atividade-'+esc(a.id)+'/capitulo-'+esc(c.id)+'">'+esc(c.title)+'</a>').join('')+'</nav>'+a.chapters.map(c=>'<section class="chapter'+(c.subchapter?' subchapter':'')+'" id="capitulo-'+esc(c.id)+'"><h2>'+esc(c.title)+'</h2><div class="prose">'+c.html+'</div></section>').join('');
  if(a.type==='quiz'){let number=0;body+=a.questionIds.map(id=>{const q=db.questions[id];return question(q,q.type==='description'?number:number++);}).join('');}
  if(a.url)body+='<p><a href="'+esc(a.url)+'"'+(a.url.startsWith('http')?' target="_blank" rel="noopener"':'')+'>Abrir referência original ↗</a></p>';
  body+=attachments(a);
  if(section){const ids=section.activityIds.filter(id=>db.activities[id].type!=='label'),index=ids.indexOf(a.id);body+='<nav class="paging" aria-label="Materiais da seção">'+(index>0?link(ids[index-1],'← Material anterior'):'<span></span>')+(index<ids.length-1?link(ids[index+1],'Próximo material →'):'<span></span>')+'</nav>';}
  return body;
}
function fileList(query=''){
  const files=db.files.filter(f=>!f.derivedFrom&&normalize(f.names.join(' ')).includes(normalize(query))).sort((a,b)=>a.names[0].localeCompare(b.names[0],'pt-BR',{numeric:true}));
  return files.map(f=>'<article class="file-row"><div class="file-title">'+esc(f.names[0])+'</div><div class="file-meta">'+esc(f.mime)+' · '+bytes(f.bytes)+'</div><div class="file-links"><a href="'+esc(f.url)+'" download="'+esc(f.names[0])+'">Baixar arquivo</a>'+(f.mime==='application/pdf'?'<a href="'+esc(f.url)+'" target="_blank" rel="noopener">Abrir PDF ↗</a>':'')+(f.playUrl?'<a href="#videos">Assistir à versão para navegador →</a>':'')+'</div>'+(f.mime.startsWith('audio/')?'<details><summary>Ouvir áudio</summary><audio controls preload="none" src="'+esc(f.url)+'"></audio></details>':'')+(f.mime.startsWith('image/')?'<details><summary>Ver imagem</summary><img loading="lazy" src="'+esc(f.url)+'" alt="'+esc(f.names[0])+'"></details>':'')+'</article>').join('')||'<p class="empty">Nenhum arquivo encontrado.</p>';
}
function videoName(name){
  const family=name.includes('Espaco')?'Espaços da clave de fá':name.includes('Linhas')?'Linhas da clave de fá':'Notas na clave de fá';
  const speed=name.includes('Lento')?'Lento':name.includes('Medio')?'Médio':'Rápido';return family+' · '+speed;
}
function videos(){return '<p class="eyebrow">VÍDEOS RECUPERADOS DO SEGUNDO BACKUP</p><h1>Memorização das notas</h1><p class="lead">Treinamentos de leitura na clave de fá em três velocidades. Os vídeos estão disponíveis neste acervo, com os arquivos originais para download.</p><div class="video-list">'+db.localVideos.map(v=>'<figure class="local-video"><video controls preload="none" src="'+esc(v.playUrl)+'" aria-label="'+esc(videoName(v.name))+'"></video><div class="caption"><h2>'+esc(videoName(v.name))+'</h2><a href="'+esc(v.playUrl)+'" download="'+esc(v.name.replace(/\.flv$/,'.mp4'))+'">Baixar vídeo MP4</a><a href="'+esc(v.originalUrl)+'" download="'+esc(v.name)+'">Original FLV</a></div></figure>').join('')+'</div>';}
function about(){return '<p class="eyebrow">SOBRE O RESGATE</p><h1>Um acervo para retomar os estudos</h1><div class="prose"><p>Este acervo reúne o curso <strong>'+esc(db.title)+'</strong>, de Prof. Glauber Lúcio Alves Santiago, recuperado de dois backups de 19 de novembro de 2020.</p><p>A versão principal conserva a organização das oito unidades e as atividades do backup Moodle mais recente. A versão anterior reúne os conteúdos da segunda cópia, com seus livros, materiais e atividades.</p><p>Os PDFs, partituras do MuseScore, imagens e áudios contidos nos backups estão disponíveis para consulta e download. Nove vídeos locais foram preparados para reprodução no navegador, com os originais preservados.</p><p>As aulas vinculadas ao YouTube mantêm suas referências originais. Esses vídeos externos dependem da disponibilidade no YouTube e de conexão com a internet.</p><p>Os enunciados, alternativas e gabaritos foram preservados para estudo independente. As orientações históricas sobre avaliações, envio e interação fazem parte do conteúdo recuperado.</p></div><h2>Materiais ausentes nos backups</h2><p class="lead">'+db.missingFiles.length+' arquivos de áudio e imagem estavam referenciados como atalhos para áreas privadas do Moodle, sem seus conteúdos nos backups. Os pontos afetados estão identificados nas atividades.</p><details><summary>Consultar a lista dos arquivos ausentes</summary><ul>'+db.missingFiles.map(f=>'<li>'+esc(f.filename)+'</li>').join('')+'</ul></details><div class="note">Anexos de correio interno, contas, tentativas e registros administrativos não integram este acervo didático.</div><p><a href="docs/recovery-report.json" target="_blank">Relatório da recuperação</a> · <a href="docs/file-integrity.json" target="_blank">Integridade dos arquivos preservados</a></p>';}
function render(){
  const hash=decodeURIComponent(location.hash.slice(1)||'inicio');active=hash;
  let markup,title=db.title,chapter;
  if(hash==='inicio')markup=home();
  else if(hash.startsWith('secao-')){const s=db.sections.find(s=>s.id===hash.slice(6));if(s){markup=sectionView(s);title=s.name;}}
  else if(hash.startsWith('atividade-')){const [id,suffix]=hash.slice(10).split('/capitulo-'),a=db.activities[id];if(a){markup=activity(a,suffix);title=a.name;chapter=suffix;}}
  else if(hash==='biblioteca')markup='<p class="eyebrow">ARQUIVOS RECUPERADOS</p><h1>Biblioteca de materiais</h1><p class="lead">Partituras, livros, áudios e outros materiais contidos nas duas cópias do curso.</p><label class="sr-only" for="file-filter">Filtrar arquivos</label><input id="file-filter" class="file-filter" type="search" placeholder="Filtrar pelo nome do arquivo…" value="'+esc(libraryFilter)+'"><div id="file-list">'+fileList(libraryFilter)+'</div>';
  else if(hash==='videos')markup=videos();
  else if(hash==='sobre')markup=about();
  else if(hash==='questoes')markup='<p class="eyebrow">ENUNCIADOS E RESPOSTAS PRESERVADOS</p><h1>Banco de questões</h1><p class="lead">Todas as questões recuperadas, incluindo versões presentes nos dois backups. Para seguir a sequência de cada atividade, abra o questionário correspondente na unidade.</p>'+Object.values(db.questions).map(question).join('');
  else if(hash.startsWith('busca/')){const query=hash.slice(6),results=Object.values(db.activities).filter(a=>a.type!=='label'&&normalize(a.name+' '+plain(a.intro)+' '+plain(a.html)+' '+a.chapters.map(c=>c.title+' '+plain(c.html)).join(' ')).includes(normalize(query)));markup='<p class="eyebrow">BUSCA NO ACERVO</p><h1>Resultados para “'+esc(query)+'”</h1><p class="lead">'+results.length+' materiais e atividades encontrados.</p><div class="resource-list">'+results.map(a=>'<a class="resource" href="#atividade-'+esc(a.id)+'"><div><strong>'+esc(a.name)+'</strong><small>'+esc(types[a.type])+(a.source==='secondary'?' · versão anterior':'')+'</small></div><span aria-hidden="true">→</span></a>').join('')+'</div>';}
  if(!markup)markup='<h1>Conteúdo não encontrado</h1><p><a href="#inicio">Voltar ao acervo</a></p>';
  $('content').innerHTML=markup;document.title=title+' · Acervo de Leitura Musical';
  document.querySelectorAll('#navigation a').forEach(a=>a.toggleAttribute('aria-current',a.hash==='#'+hash));
  if(hash.startsWith('atividade-')||hash.startsWith('secao-')){const s=hash.startsWith('atividade-')?sectionOf(hash.slice(10).split('/')[0]):db.sections.find(s=>s.id===hash.slice(6));document.querySelectorAll('[data-section]').forEach(node=>{node.open=node.dataset.section===s?.id;});}
  $('sidebar').classList.remove('open');$('nav-toggle').setAttribute('aria-expanded','false');
  if(chapter){requestAnimationFrame(()=>document.getElementById('capitulo-'+chapter)?.scrollIntoView({block:'start'}));}
  else window.scrollTo({top:0});
}
$('nav-toggle').addEventListener('click',()=>{$('sidebar').classList.toggle('open');$('nav-toggle').setAttribute('aria-expanded',String($('sidebar').classList.contains('open')));});
$('search-form').addEventListener('submit',event=>{event.preventDefault();const q=$('search').value.trim();if(q)location.hash='busca/'+encodeURIComponent(q);});
$('content').addEventListener('input',event=>{if(event.target.id==='file-filter'){libraryFilter=event.target.value;$('file-list').innerHTML=fileList(libraryFilter);}});
$('content').addEventListener('click',event=>{const button=event.target.closest('.video-trigger');if(!button)return;const id=button.dataset.video;if(!/^[\w-]{11}$/.test(id))return;const frame=document.createElement('iframe');frame.src='https://www.youtube-nocookie.com/embed/'+id;frame.title='Vídeo aula de leitura musical';frame.allow='fullscreen; encrypted-media; picture-in-picture';frame.allowFullscreen=true;frame.referrerPolicy='strict-origin-when-cross-origin';button.replaceWith(frame);});
window.addEventListener('hashchange',render);
try{const response=await fetch('course.json');if(!response.ok)throw new Error('Conteúdo indisponível');db=await response.json();nav();render();}catch(error){$('content').innerHTML='<div class="loading-error"><h1>Não foi possível abrir o acervo</h1><p>Verifique a conexão e recarregue a página para tentar novamente.</p></div>';console.error(error);}
