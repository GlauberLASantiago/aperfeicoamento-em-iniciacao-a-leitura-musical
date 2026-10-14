"""Recover Moodle backup content as static JSON and byte-exact public course files."""
import argparse, collections, hashlib, html, json, re, shutil, unicodedata, zipfile, mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--secondary',type=Path)
parser.add_argument('--converted',type=Path)
args=parser.parse_args();SRC=args.source.resolve();OUT=args.output.resolve()
(OUT/'files').mkdir(parents=True,exist_ok=True);(OUT/'docs').mkdir(exist_ok=True)
def txt(el,key,default=''):
    val=el.findtext(key)
    return default if val in (None,'$@NULL@$') else val
def norm(s):return unicodedata.normalize('NFC',unquote(s)).lstrip('/')
records=[];excluded=0;assets={};missing=[];external=set();video_ids=set();absent=[];nested={}
file_elements=ET.parse(SRC/'files.xml').getroot().findall('file')
for el in file_elements:
    digest=txt(el,'contenthash');source=SRC/'files'/digest[:2]/digest
    if txt(el,'component')=='block_jmail' or not txt(el,'filename').lower().endswith('.zip') or not source.exists():continue
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or entry.file_size>50_000_000:continue
            blob=archive.read(entry);nested[hashlib.sha1(blob).hexdigest()]=(blob,Path(entry.filename).name)
for el in ET.parse(SRC/'files.xml').getroot().findall('file'):
    if txt(el,'filename')=='.':continue
    if txt(el,'component')=='block_jmail':excluded+=1;continue
    rec={key:txt(el,key) for key in ['contenthash','contextid','component','filearea','itemid','filepath','filename','filesize','mimetype']}
    digest=rec['contenthash'];source=SRC/'files'/digest[:2]/digest
    if not source.exists():source=SRC/'files'/digest
    if source.exists():blob=source.read_bytes()
    elif digest in nested:blob=nested[digest][0]
    else:
        rec.update({'url':None,'available':False,'size':int(rec['filesize'] or '0')});records.append(rec)
        absent.append({'filename':rec['filename'],'sha1':digest,'mime':rec['mimetype'],'reason':'Referenced Moodle user repository file absent from backup'})
        continue
    assert hashlib.sha1(blob).hexdigest()==digest
    suffix=Path(rec['filename']).suffix.lower()
    if not re.fullmatch(r'\.[a-z0-9]{1,8}',suffix):suffix='.bin'
    rec['url']='files/'+digest+suffix
    destination=OUT/rec['url'];destination.write_bytes(blob)
    rec['size']=len(blob);rec['available']=True;records.append(rec)
    if rec['url'] not in assets:
        assets[rec['url']]={'url':rec['url'],'sha1':digest,'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob),'mime':rec['mimetype'],'names':[]}
    if rec['filename'] not in assets[rec['url']]['names']:assets[rec['url']]['names'].append(rec['filename'])
legacy_files={};legacy_links={};legacy_root=None;legacy_records=[]
if args.secondary:
    legacy_root=ET.parse(args.secondary/'moodle.xml').getroot()
    for section in legacy_root.findall('COURSE/SECTIONS/SECTION'):
        for item in section.findall('MODS/MOD'):legacy_links[txt(item,'ID')]='anterior-'+txt(item,'INSTANCE')
    for path in sorted((args.secondary/'course_files').rglob('*')):
        if not path.is_file():continue
        blob=path.read_bytes();digest=hashlib.sha1(blob).hexdigest();suffix=path.suffix.lower();url='files/'+digest+suffix
        (OUT/url).write_bytes(blob);relative=path.relative_to(args.secondary/'course_files').as_posix()
        mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        rec={'contenthash':digest,'url':url,'filename':path.name,'filepath':'/'+str(Path(relative).parent).replace('\\','/')+'/','mimetype':mime,'size':len(blob),'available':True,'component':'legacy_course','contextid':'secondary','itemid':'0','filearea':'content','source':'secondary','originalPath':relative}
        if url not in assets:assets[url]={'url':url,'sha1':digest,'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob),'mime':mime,'names':[path.name],'source':'secondary'}
        elif path.name not in assets[url]['names']:assets[url]['names'].append(path.name)
        if suffix=='.flv' and args.converted and (args.converted/(digest+'.mp4')).exists():
            video=(args.converted/(digest+'.mp4')).read_bytes();video_hash=hashlib.sha1(video).hexdigest();play='files/'+video_hash+'.mp4';(OUT/play).write_bytes(video);rec['playUrl']=play;assets[url]['playUrl']=play
            assets[play]={'url':play,'sha1':video_hash,'sha256':hashlib.sha256(video).hexdigest(),'bytes':len(video),'mime':'video/mp4','names':[path.stem+'.mp4'],'source':'converted','derivedFrom':url}
        legacy_files[norm(relative)]=rec;legacy_records.append(rec);records.append(rec)
activity_roots={}
if args.secondary:
    for archive_path in (args.secondary/'course_files').rglob('*.zip'):
        with zipfile.ZipFile(archive_path) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or entry.file_size>50_000_000:continue
                blob=archive.read(entry);nested.setdefault(hashlib.sha1(blob).hexdigest(),(blob,Path(entry.filename).name))
for digest,(blob,name) in nested.items():
    suffix=Path(name).suffix.lower()
    if suffix not in {'.mp3','.png','.jpg','.jpeg','.gif','.pdf','.mus','.mscz','.doc','.docx'}:continue
    url='files/'+digest+suffix
    if url not in assets:
        (OUT/url).write_bytes(blob);mime=mimetypes.guess_type(name)[0] or 'application/octet-stream'
        assets[url]={'url':url,'sha1':digest,'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob),'mime':mime,'names':[name],'source':'nested-archive'}
for directory in (SRC/'activities').iterdir():
    kind=directory.name.rsplit('_',1)[0]
    root=ET.parse(directory/(kind+'.xml')).getroot()
    activity_roots[root.get('moduleid')]=(root,root.find(kind),kind,directory)
def find_file(name,scope):
    name=norm(name)
    candidates=[r for r in records if norm(r['filepath']+r['filename'])==name]
    for key in ['itemid','contextid','component','filearea']:
        wanted=scope.get(key)
        filtered=[r for r in candidates if r[key]==str(wanted)]
        if wanted is not None and filtered:candidates=filtered
    if len({r['url'] for r in candidates})==1:return candidates[0]
    return None
def rewrite(url,scope):
    url=html.unescape(url).strip()
    if url.startswith(('javascript:','data:','vbscript:')):return ''
    if '@@PLUGINFILE@@' in url:
        name=url.split('@@PLUGINFILE@@',1)[1].lstrip('/')
        rec=find_file(name,scope)
        if rec and rec['url']:return rec['url']
        missing.append({'location':scope.get('location'),'reference':url,'reason':'No unambiguous file in backup'})
        return ''
    parsed=urlparse(url)
    if 'pluginfile.php/' in parsed.path:
        parts=parsed.path.split('pluginfile.php/',1)[1].split('/')
        if len(parts)>=5:
            local={'contextid':parts[0],'component':parts[1],'filearea':parts[2],'itemid':parts[3],**{'location':scope.get('location')}}
            rec=find_file('/'.join(parts[4:]),local)
            if rec and rec['url']:return rec['url']
        missing.append({'location':scope.get('location'),'reference':url,'reason':'Historical pluginfile not found in backup'})
        return ''
    is_moodle='@@MOODLE@@' in url or ('ufscar.br' in parsed.netloc and '.php' in parsed.path)
    if is_moodle:
        if '/file.php/' in parsed.path:
            parts=parsed.path.split('/file.php/',1)[1].split('/',1)
            rec=legacy_files.get(norm(parts[1])) if len(parts)>1 else None
            if rec:return rec['url']
        ident=parse_qs(parsed.query).get('id',[''])[0]
        if scope.get('legacy') and '/mod/' in parsed.path and ident in legacy_links:return '#atividade-'+legacy_links[ident]
        if '/mod/' in parsed.path and ident in activity_roots:
            chapter=parse_qs(parsed.query).get('chapterid',[''])[0]
            return '#atividade-'+ident+('/capitulo-'+chapter if chapter else '')
        if '/course/view.php' in parsed.path and ident=='764':return '#inicio'
        missing.append({'location':scope.get('location'),'reference':url,'reason':'Moodle service or destination outside backup'})
        return ''
    if url.startswith('http://'):url='https://'+url[7:]
    if url.startswith(('http://','https://')):external.add(url)
    return url
def youtube(url):
    match=re.search(r'(?:youtube(?:-nocookie)?\.com/(?:embed/|v/)|youtu\.be/)([\w-]{11})',html.unescape(url))
    if not match:
        parsed=urlparse(html.unescape(url))
        if 'youtube.com' in parsed.netloc:
            vid=parse_qs(parsed.query).get('v',[''])[0]
            return vid if re.fullmatch(r'[\w-]{11}',vid) else None
    return match.group(1) if match else None
def video_block(soup,vid):
    video_ids.add(vid);box=soup.new_tag('div',attrs={'class':'video-card'})
    button=soup.new_tag('button',attrs={'type':'button','class':'video-trigger','data-video':vid});button.string='Carregar vídeo do YouTube';box.append(button)
    link=soup.new_tag('a',href='https://www.youtube.com/watch?v='+vid,attrs={'target':'_blank','rel':'noopener'});link.string='Abrir no YouTube ↗';box.append(link);return box
def clean(content,scope):
    soup=BeautifulSoup(content or '', 'html.parser')
    for el in list(soup.find_all(['iframe','object','embed'])):
        if el.parent is None:continue
        candidates=[el.get('src',''),el.get('data','')]+[p.get('value','') for p in el.find_all('param')]
        vid=next((youtube(u) for u in candidates if youtube(u)),None)
        if vid:el.replace_with(video_block(soup,vid))
        else:
            link=el.get('src') or el.get('data')
            if link:
                href=rewrite(link,scope)
                if href:
                    a=soup.new_tag('a',href=href,attrs={'target':'_blank','rel':'noopener'});a.string='Abrir conteúdo externo ↗';el.replace_with(a);continue
            el.decompose()
    for el in list(soup.find_all(['script','style','form','input','textarea','select','param'])):el.decompose()
    keep={'p','div','span','h1','h2','h3','h4','h5','h6','strong','b','em','i','u','s','small','sub','sup','br','hr','ul','ol','li','table','thead','tbody','tfoot','tr','td','th','blockquote','pre','code','a','img','audio','video','source','button','figure','figcaption'}
    for el in list(soup.find_all(True)):
        if el.name not in keep:el.unwrap();continue
        if el.name=='h1':el.name='h2'
        attrs={}
        for key in ['alt','title','colspan','rowspan','controls','preload','type','data-video']:
            if key in el.attrs:attrs[key]=el.attrs[key]
        if el.get('class') in (['video-card'],['video-trigger']):attrs['class']=el.get('class')
        for key in ['src','href']:
            if key in el.attrs:
                value=rewrite(el.attrs[key],scope)
                if value:attrs[key]=value
        el.attrs=attrs
        if el.name=='img':
            if not el.get('src'):
                replacement=soup.new_tag('span',attrs={'class':'unavailable'});replacement.string=el.get('alt') or 'Imagem não incluída no backup';el.replace_with(replacement);continue
            el['loading']='lazy'
        if el.name=='a':
            if not el.get('href'):
                el.name='span';el['class']='archived-reference'
                if not el.get_text(strip=True):el.string='Referência do Moodle original'
                continue
            if el['href'].startswith('http'):el['target']='_blank';el['rel']='noopener'
            rec=next((r for r in records if r['url']==el['href']),None)
            if not el.get_text(strip=True) and not el.find('img'):el.string=rec['filename'] if rec else 'Abrir referência'
    for el in list(soup.find_all('a')):
        rec=next((r for r in records if r['url']==el.get('href')),None)
        if rec and rec['mimetype'].startswith('audio/'):
            box=soup.new_tag('figure',attrs={'class':'audio-card'})
            audio=soup.new_tag('audio',src=rec['url'],attrs={'controls':'','preload':'none'});box.append(audio)
            caption=soup.new_tag('figcaption');link=soup.new_tag('a',href=rec['url'],attrs={'download':rec['filename']});link.string=el.get_text(strip=True) or 'Baixar áudio';caption.append(link);box.append(caption);el.replace_with(box)
        elif rec and rec.get('playUrl'):
            box=soup.new_tag('figure',attrs={'class':'local-video'});video=soup.new_tag('video',src=rec['playUrl'],attrs={'controls':'','preload':'metadata'});box.append(video);el.replace_with(box);box.append(el)
    return str(soup)
def scope(root,kind,area,itemid='0',location=''):
    return {'contextid':root.get('contextid'),'component':'mod_'+kind,'filearea':area,'itemid':itemid,'location':location}
questions={}
for category in ET.parse(SRC/'questions.xml').getroot().findall('question_category'):
    for el in category.findall('./questions/question'):
        qid=el.get('id');qscope={'component':'question','itemid':qid,'filearea':'questiontext','location':'question-'+qid}
        q={'id':qid,'type':txt(el,'qtype'),'name':txt(el,'name'),'html':clean(txt(el,'questiontext'),qscope),'feedback':clean(txt(el,'generalfeedback'),{**qscope,'filearea':'generalfeedback'}),'category':txt(category,'name'),'answers':[]}
        if not q['html'].strip():q['html']='<p>'+html.escape(q['name'])+'</p>'
        for answer in el.findall('.//answers/answer'):
            aid=answer.get('id')
            q['answers'].append({'id':aid,'html':clean(txt(answer,'answertext'),{**qscope,'itemid':aid,'filearea':'answer'}),'fraction':float(txt(answer,'fraction','0')),'feedback':clean(txt(answer,'feedback'),{**qscope,'itemid':aid,'filearea':'answerfeedback'})})
        q['selfAssessment']=bool(q['answers']) and all('acertei' in BeautifulSoup(a['html'],'html.parser').get_text().lower() for a in q['answers'])
        q['selfAssessment']=q['selfAssessment'] or '_resp' in q['name'].lower()
        q['unavailableFiles']=list(dict.fromkeys(r['filename'] for r in records if not r['available'] and r['component']=='question' and r['itemid'] in {qid,*[a['id'] for a in q['answers']]}))
        questions[qid]=q
activities={}
for mid,(root,el,kind,directory) in activity_roots.items():
    intro=clean(txt(el,'intro'),scope(root,kind,'intro',location='activity-'+mid))
    module=ET.parse(directory/'module.xml').getroot()
    a={'id':mid,'type':kind,'name':txt(el,'name') or kind,'intro':intro,'hidden':module.findtext('.//visible')=='0','chapters':[],'files':[]}
    if kind=='label':
        plain=BeautifulSoup(intro,'html.parser').get_text(' ',strip=True)
        a['name']=plain[:95] or 'Separador do curso'
    if kind=='page':a['html']=clean(txt(el,'content'),scope(root,kind,'content',location='activity-'+mid))
    if kind=='book':
        for c in sorted(el.findall('./chapters/chapter'),key=lambda x:int(txt(x,'pagenum','0'))):
            a['chapters'].append({'id':c.get('id'),'title':txt(c,'title'),'subchapter':txt(c,'subchapter')=='1','hidden':txt(c,'hidden')=='1','html':clean(txt(c,'content'),scope(root,kind,'chapter',c.get('id'),'chapter-'+c.get('id')))})
    if kind=='quiz':
        a['questionIds']=[qid for qid in txt(el,'questions').split(',') if qid not in ('','0')]
        assert all(qid in questions for qid in a['questionIds']),mid
    if kind=='url':a['url']=rewrite(txt(el,'externalurl'),scope(root,kind,'intro',location='activity-'+mid))
    for r in records:
        if r['contextid']==root.get('contextid') and r['component']=='mod_'+kind:
            f={k:r[k] for k in ['url','filename','mimetype','size','available']}
            if f not in a['files']:a['files'].append(f)
    activities[mid]=a
legacy_sections=[]
if legacy_root is not None:
    legacy_scope={'legacy':True,'location':'secondary'}
    for el in legacy_root.iter('QUESTION'):
        if not txt(el,'QTYPE'):continue
        qid='anterior-'+txt(el,'ID');sc={**legacy_scope,'location':'question-'+qid}
        q={'id':qid,'type':txt(el,'QTYPE'),'name':txt(el,'NAME'),'html':clean(txt(el,'QUESTIONTEXT'),sc),'feedback':clean(txt(el,'GENERALFEEDBACK'),sc),'category':'Versão anterior','answers':[],'source':'secondary'}
        if not q['html'].strip():q['html']='<p>'+html.escape(q['name'])+'</p>'
        for answer in el.findall('./ANSWERS/ANSWER'):
            q['answers'].append({'id':'anterior-'+txt(answer,'ID'),'html':clean(txt(answer,'ANSWER_TEXT'),sc),'fraction':float(txt(answer,'FRACTION','0')),'feedback':clean(txt(answer,'FEEDBACK'),sc)})
        q['selfAssessment']=bool(q['answers']) and all('acertei' in BeautifulSoup(a['html'],'html.parser').get_text().lower() for a in q['answers'])
        questions[qid]=q
    for el in legacy_root.findall('COURSE/MODULES/MOD'):
        mid='anterior-'+txt(el,'ID');kind=txt(el,'MODTYPE');sc={**legacy_scope,'location':'activity-'+mid}
        a={'id':mid,'type':kind,'name':txt(el,'NAME') or kind,'intro':clean(txt(el,'INTRO') or txt(el,'SUMMARY'),sc),'hidden':False,'chapters':[],'files':[],'source':'secondary'}
        if kind=='label':
            a['intro']=clean(txt(el,'CONTENT'),sc);a['name']=BeautifulSoup(a['intro'],'html.parser').get_text(' ',strip=True)[:95] or 'Separador da versão anterior'
        if kind=='resource':
            a['html']=clean(txt(el,'ALLTEXT'),sc)
            if txt(el,'REFERENCE'):a['url']=rewrite(txt(el,'REFERENCE'),sc)
        if kind=='book':
            for c in sorted(el.findall('./CHAPTERS/CHAPTER'),key=lambda x:int(txt(x,'PAGENUM','0'))):
                cid='anterior-'+txt(c,'ID');a['chapters'].append({'id':cid,'title':txt(c,'TITLE'),'subchapter':txt(c,'SUBCHAPTER')=='1','hidden':txt(c,'HIDDEN')=='1','html':clean(txt(c,'CONTENT'),{**sc,'location':'chapter-'+cid})})
        if kind=='quiz':
            a['questionIds']=['anterior-'+qid for qid in txt(el,'QUESTIONS').split(',') if qid not in ('','0')]
            assert all(qid in questions for qid in a['questionIds']),mid
        activities[mid]=a
    for el in legacy_root.findall('COURSE/SECTIONS/SECTION'):
        ids=['anterior-'+txt(item,'INSTANCE') for item in el.findall('MODS/MOD') if 'anterior-'+txt(item,'INSTANCE') in activities]
        summary=clean(txt(el,'SUMMARY'),legacy_scope);plain=BeautifulSoup(summary,'html.parser').get_text(' ',strip=True)
        number=int(txt(el,'NUMBER','0'))
        legacy_sections.append({'id':'anterior-'+txt(el,'ID'),'number':number,'name':plain[:80] or ('Início' if not number else 'Unidade '+str(number)),'hidden':txt(el,'VISIBLE')=='0','html':summary,'activityIds':ids,'source':'secondary'})
    legacy_sections.sort(key=lambda section:section['number'])
sections=[];included=set()
for directory in (SRC/'sections').iterdir():
    el=ET.parse(directory/'section.xml').getroot();ids=[mid for mid in txt(el,'sequence').split(',') if mid in activities]
    included.update(ids);sections.append({'id':el.get('id'),'number':int(txt(el,'number','0')),'name':txt(el,'name') or 'Seção '+txt(el,'number'),'hidden':txt(el,'visible')=='0','html':clean(txt(el,'summary'),{'contextid':'117234','component':'course','filearea':'section','itemid':el.get('id'),'location':'section-'+el.get('id')}),'activityIds':ids})
sections.sort(key=lambda s:s['number'])
orphans=[mid for mid in activities if mid not in included and not mid.startswith('anterior-')]
if orphans:sections.append({'id':'adicionais','number':99,'name':'Conteúdos adicionais do backup','hidden':False,'html':'','activityIds':orphans})
sections.extend(legacy_sections)
course=ET.parse(SRC/'course/course.xml').getroot()
data={'title':txt(course,'fullname'),'summary':clean(txt(course,'summary'),{'contextid':course.get('contextid'),'component':'course','filearea':'summary','itemid':'0','location':'course'}),'backupDate':'19/11/2020','sections':sections,'activities':activities,'questions':questions,'files':list(assets.values()),'missingFiles':list({r['sha1']:r for r in absent}.values()),'localVideos':[{'name':r['filename'],'originalUrl':r['url'],'playUrl':r.get('playUrl')} for r in legacy_records if r['filename'].lower().endswith('.flv')]}
(OUT/'course.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
report={'sourceBackupSha256':'4686aad81c10a19c11258a04db45aa609a616653c852dee245bd2d4e909eb8bc','sections':len(sections),'activities':len(activities),'activityTypes':dict(collections.Counter(a['type'] for a in activities.values())),'chapters':sum(len(a['chapters']) for a in activities.values()),'questions':len(questions),'questionTypes':dict(collections.Counter(q['type'] for q in questions.values())),'quizQuestionCounts':{mid:len(a['questionIds']) for mid,a in activities.items() if a['type']=='quiz'},'courseFileReferences':len(records),'uniquePublicFiles':len(assets),'publicBytes':sum(a['bytes'] for a in assets.values()),'excludedPrivateMailAttachmentRecords':excluded,'missingReferences':list({(r['location'],r['reference']):r for r in missing}.values()),'externalReferences':sorted(external),'youtubeVideoIds':sorted(video_ids),'learnerAccountsExported':False,'quizAttemptsExported':False,'forumPostsExported':False,'rawBackupPublished':False}
report.update({'secondaryBackupSha256':'45d49d58e656e81eead4e2430db1bc417ba9d35153dc95ccb72e4407388ae37e' if args.secondary else None,'primaryActivities':sum(a.get('source')!='secondary' for a in activities.values()),'secondaryActivities':sum(a.get('source')=='secondary' for a in activities.values()),'unavailableFileReferences':len(absent),'unavailableUniqueFiles':len(data['missingFiles']),'unavailableFiles':data['missingFiles'],'localVideoCount':len(data['localVideos'])})
(OUT/'docs/recovery-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'docs/file-integrity.json').write_text(json.dumps(list(assets.values()),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('missingReferences','externalReferences','youtubeVideoIds')},ensure_ascii=True,indent=2))
print('Missing references:',len(report['missingReferences']),'YouTube links:',len(video_ids))

