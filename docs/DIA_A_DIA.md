# Dia a dia & melhores práticas

Guia prático pro seu uso real (pesquisa de segurança/OWASP, muitos links e PDFs,
vários dispositivos). Tudo roda local, conteúdo em pt-BR.

## O que JÁ funciona (verificado)
- Pipeline mecânico completo: capturar → buscar → extrair → política → dedupe → scout → curar → indexar. 44 testes passando.
- Ingestão real de X/Twitter, artigos, PDF (camada de texto), Markdown/TXT, GitHub, notas; import em lote (pasta + arquivo de links).
- Jev em `mock` determinístico (roteia Sonnet/Opus, dedupe) — offline, sem token.
- Segurança: confinamento de path, SSRF guard, permissões do Claude, **camada anti-prompt-injection**, política de dados sensíveis (inclui **financeiro** agora).
- `claude` já está logado nesta máquina → dá pra usar `--claude`.

## O que FALTA habilitar (passo a passo)
1. **Config local** (1x): `./scripts/bootstrap.ps1` (cria `config.yaml`, `.env`).
2. **Obsidian Sync**: abrir `C:\SecondBrain` como vault e ativar Sync. Sincronizar só `wiki/`, `raw/inbox/`, `raw/archive/`, `templates/`. **NÃO** sincronizar `state/`, `logs/`, `backups/`, `.venv/`, `.git/`, `.env`, `config/config.yaml`, `.claude/`. (ver `REMOTE_ACCESS.md`)
3. **Tarefas agendadas**: `./scripts/register-tasks.ps1` (ingestão a cada 20 min + noturno 02:00). Confere com `Get-ScheduledTask -TaskPath '\SecondBrain\'`.
4. **Backup**: escolha um destino FORA do vault/sync, ex.: `./scripts/backup.ps1 -Destination D:\Backups\SecondBrain -Password <senha>` (precisa 7-Zip p/ criptografar). Teste um restore (trimestral).
5. **Captura no celular**: seguir `IOS_CAPTURE.md` / `ANDROID_CAPTURE.md` (Share → Obsidian + Web Clipper).
6. **Remote Control** (falar com o Claude pelo celular): `claude remote-control --name "Second Brain"` na pasta do projeto.
7. **Jev live (opcional)**: só se quiser o roteador real — `cmdkey /generic:SecondBrain/TypeSafe /user:token /pass:<TOKEN>` + `JEV_MODE=live`. O `mock` já resolve bem no começo.

## Rotina diária sugerida
- **Durante o dia (capturar sem fricção):** mande links/artigos pelo Share Sheet (celular) ou cole num `links.txt` e rode `secondbrain capture-links links.txt`. PDFs: jogue em `raw/inbox/` ou `secondbrain import-file <arquivo>`.
- **Processar:** a tarefa agendada importa a cada 20 min. Manual: `secondbrain process-inbox` (ou `--claude` p/ resumos/curadoria de verdade).
- **Manhã (5 min):** leia `reports/latest.md` — pendências, duplicatas, `needs_review`, conflitos, integridade de links. Aprove/edite o que a noite propôs. Nada é aplicado sem você.
- **Perguntar à base:** `secondbrain ask "..."` (ou a skill `ask` no Claude) — simples vai pro Sonnet, complexo pro Opus.
- **Noite (automático 02:00):** lint + curadoria + relatório + checkpoint git + backup.

## Melhores práticas pro seu perfil
- **Dados sensíveis (pentest/cliente/financeiro):** a política marca como `needs_review` e **não sincroniza nem manda pro Jev/Claude**. Para material realmente sigiloso (ex.: seu `~/LifeOS` com extratos bancários, loot de engagements, relatórios de cliente) use um **vault separado NÃO sincronizado** — não jogue no vault pessoal que vai pro celular. Posso montar esse segundo vault quando quiser.
- **Repo público:** é só o **projeto** — seus dados (`raw/`, páginas de `wiki/`) estão no `.gitignore` e nunca sobem. Confirma com `git status` antes de qualquer push.
- **Prompt injection:** você vai capturar muito conteúdo hostil (CTF/bug bounty). Trechos entram **cercados** e marcados `injection_flags`; o scout/librarian tratam como dado inerte. Reveja páginas com callout `[!danger]` antes de curar.
- **Nunca** aprove um "always allow" amplo no meio de um run do Claude (o contrato alerta sobre isso).
- **LifeOS/Fabric:** o LifeOS que achei (`~/LifeOS` no Kali) é majoritariamente financeiro → trate como sigiloso (acima). Se quiser as *notas* (não os extratos), filtramos por tipo no import.
- **Backup ≠ Sync ≠ Git:** Sync replica entre aparelhos, Git versiona o **framework**, backup (`backup.ps1`) é o que recupera seus **dados**. Mantenha os três.

## Comandos que você mais vai usar
```powershell
secondbrain capture-url "<url>" --title "nota" --tags owasp,web
secondbrain capture-links links.txt
secondbrain import-folder "C:\caminho\pdfs" --glob *.pdf
secondbrain process-inbox            # + --claude para enriquecer
secondbrain ask "o que salvei sobre SSRF?"
secondbrain report ; secondbrain lint
```
