# Aperfeiçoamento em Iniciação à Leitura Musical

Acervo estático do curso de Prof. Glauber Lúcio Alves Santiago, recuperado de dois backups Moodle de 19/11/2020. Reúne as oito unidades da versão principal e uma versão anterior, identificada separadamente. Funciona no navegador sem servidor Moodle, contas ou banco de dados.

## Conteúdo recuperado

- 179 entradas de materiais e atividades: 120 da versão principal e 59 da anterior.
- 25 livros, com 82 capítulos; páginas, orientações, propostas de fóruns e tarefas.
- Cinco questionários e um banco com 103 registros: 56 questões de múltipla escolha, 46 enunciados e uma questão discursiva. Alguns conteúdos se repetem entre as versões.
- 203 arquivos únicos, incluindo PDFs, partituras, imagens, áudios, arquivos de edição e vídeos.
- Nove vídeos FLV convertidos para MP4 (H.264/AAC), com os originais preservados para download.
- Busca de conteúdos, biblioteca de arquivos e respostas/partituras para autoavaliação.

São preservados também os materiais originalmente ocultos e os gabaritos para tutores, por se tratar de um acervo para estudo. Os questionários não registram tentativas nem enviam respostas. Tarefas, fóruns e chat conservam suas orientações, sem envio, discussão, presença, notas ou certificação.

## Limites da recuperação

O backup principal referencia **40 arquivos únicos de áudio/imagem que não estão nos arquivos fornecidos**: são aliases de um repositório privado do Moodle, com 166 referências. A comparação por SHA-1 com os arquivos da segunda cópia e os ZIPs internos não encontrou esses conteúdos. O site sinaliza essas ausências; não foram fabricados substitutos. Isso afeta sobretudo o ditado 1.4 da versão principal.

Vídeos externos continuam dependendo do YouTube. Links antigos para serviços Moodle que não puderam ser recuperados ficam sinalizados. Nem todos os vídeos externos tiveram sua disponibilidade atual verificada.

Não são publicados os backups completos, XMLs administrativos, contas, notas ou tentativas. Foram excluídos 21 registros de anexos do correio interno (`block_jmail`), incluindo trabalhos de participantes. Os documentos pedagógicos preservam os créditos presentes nos originais.

## Uso local

Requer Node.js. Sem dependências npm:

```sh
npm start
```

Abra `http://127.0.0.1:4194/`. Para verificar a integridade e as referências:

```sh
npm test
```

Pode ser hospedado diretamente no GitHub Pages, na raiz da branch `main`. Não depende de uma aplicação de backend.

## Origem e reprodução

- Backup principal: `backup-moodle2-course-764-ailm-20201119-1005-nu.mbz`, SHA-256 `4686aad81c10a19c11258a04db45aa609a616653c852dee245bd2d4e909eb8bc`.
- Backup anterior: `Aperfeicoamento_em_iniciacao_a_leitura_musical_backup-aperinileitmus-20201119-1147.zip`, SHA-256 `45d49d58e656e81eead4e2430db1bc417ba9d35153dc95ccb72e4407388ae37e`.

Os dois arquivos são ZIPs. Antes de extrair, valide que cada destino permanece dentro da pasta de extração e rejeite links simbólicos. Os backups não fazem parte deste repositório.

O gerador `scripts/recover_course.py` requer Python e BeautifulSoup4. Recebe as pastas já extraídas e, opcionalmente, a pasta com os vídeos convertidos:

```sh
python -m pip install beautifulsoup4
python scripts/convert_videos.py --help
python scripts/recover_course.py --source /pasta/backup-principal --secondary /pasta/backup-anterior --converted /pasta/videos-convertidos --output /pasta/site
```

O relatório em `docs/recovery-report.json` documenta referências não recuperadas. `docs/file-integrity.json` registra os hashes e tamanhos de todos os arquivos publicados; `docs/video-conversion.json` documenta as conversões. `npm test` compara os bytes físicos com esses registros, verifica vínculos entre seções/atividades/questões e rejeita HTML com scripts, formulários ou referências Moodle não resolvidas.
