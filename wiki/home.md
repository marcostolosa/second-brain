---
id: home
title: 🧠 Cockpit
type: home
status: active
lang: pt-BR
created: 2026-11-07T00:00:00Z
updated: 2026-11-07T00:00:00Z
---

# 🧠 SecondBrain — Cockpit

> [!tip] Página inicial. Fixe com o 📌 (ou use o plugin **Homepage** para abrir aqui ao iniciar).

## 🚀 Navegação
- [[index|📇 Índice]] — todas as páginas com resumo
- [[overview|🗺️ Overview]] — a tese atual da base
- [[log|🧾 Log]] — histórico append-only das execuções

## 🗂️ Áreas
- Fontes → pasta `sources/` · Entidades → `entities/` · Conceitos → `concepts/` · Perguntas → `questions/`

## ✅ Revisão do dia
> [!note] Relatório mais recente (gerado por `secondbrain report`; só no PC, não sincroniza)

![[latest]]

## ⚡ Ações rápidas (rode no PowerShell, em `C:\SecondBrain`)
```powershell
.\.venv\Scripts\secondbrain capture-url "<url>" --title "nota" --tags tag1,tag2
.\.venv\Scripts\secondbrain capture-links links.txt
.\.venv\Scripts\secondbrain import-folder "C:\caminho\pdfs" --glob *.pdf
.\.venv\Scripts\secondbrain process-inbox          # + --claude p/ enriquecer
.\.venv\Scripts\secondbrain ask "minha pergunta"
.\.venv\Scripts\secondbrain report
```

## ✍️ Capturar aqui no Obsidian
Crie a nota **em `raw/inbox/`** (nunca edite `wiki/` enquanto a curadoria roda). O PC processa e vira página citada. No celular: Share → Obsidian → `raw/inbox/`.

## 🕸️ Grafo
Abra o **Graph view** (ícone na lateral) para ver as conexões. Dica: filtre por `path:wiki/` e use cores por `tag:`.

---

### 🔌 Versão dinâmica (opcional — requer o plugin community **Dataview**)
Instale Dataview e substitua as listas acima por blocos como estes (cole num bloco ` ```dataview `):

- **Precisa de revisão:**
  `TABLE status, injection_flags FROM "wiki" WHERE status = "needs_review"`
- **Capturado nos últimos 7 dias:**
  `TABLE captured_at, provider FROM "wiki/sources" WHERE date(captured_at) >= date(today) - dur(7 days) SORT captured_at DESC`
- **Com sinais de injeção:**
  `LIST FROM "wiki" WHERE injection_flags`
- **Por tag:**
  `LIST FROM #owasp OR #ssrf SORT file.mtime DESC`
