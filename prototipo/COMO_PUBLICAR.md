# Como publicar o protótipo online (GitHub Pages)

Tempo estimado: 10 minutos. Gratuito. Sem instalar nada no computador.

---

## O que você vai ter no final

Um link como este:
```
https://SEU-NOME.github.io/sistema-contratos/
```

Qualquer pessoa com o link consegue abrir o sistema no navegador,
sem precisar instalar nada.

---

## Passo a passo

### 1. Criar uma conta no GitHub

Acesse https://github.com e clique em **Sign up**.
Preencha e-mail, senha e nome de usuário. É gratuito.

---

### 2. Criar o repositório do projeto

Após entrar no GitHub:

1. Clique no botão verde **New** (ou acesse https://github.com/new)
2. Preencha:
   - **Repository name:** `sistema-contratos`
   - **Description:** Sistema de gestão de contratos e faturamento
   - Marque **Public** (necessário para o GitHub Pages gratuito)
3. Clique em **Create repository**

---

### 3. Fazer upload dos arquivos

Na página do repositório recém-criado:

1. Clique em **uploading an existing file**
2. Arraste ou selecione os arquivos do projeto:
   - `prototipo.html`
   - Pasta `testes/` (com `00_dados_teste.sql` e `GUIA_DE_TESTES.md`)
   - Pastas de cada módulo (`modulo-01-clientes/`, `modulo-02-contratos/`, etc.)
3. No campo **Commit changes**, escreva: `Primeiro upload — sistema de contratos`
4. Clique em **Commit changes**

> Dica: você pode subir os arquivos aos poucos em vários commits.
> Não precisa subir tudo de uma vez.

---

### 4. Ativar o GitHub Pages

1. Na página do repositório, clique em **Settings** (ícone de engrenagem)
2. No menu lateral esquerdo, clique em **Pages**
3. Em **Source**, selecione **Deploy from a branch**
4. Em **Branch**, selecione **main** e a pasta **/ (root)**
5. Clique em **Save**

Aguarde 1–2 minutos. O GitHub vai exibir uma mensagem:
> ✅ Your site is published at https://SEU-NOME.github.io/sistema-contratos/

---

### 5. Compartilhar o protótipo

Para compartilhar o protótipo navegável diretamente, o link será:
```
https://SEU-NOME.github.io/sistema-contratos/prototipo.html
```

Envie este link para sua equipe. Qualquer pessoa pode abrir no navegador.

---

## Convidar colaboradores para o código

Para que membros da equipe possam ver e editar o código:

1. Na página do repositório, vá em **Settings → Collaborators**
2. Clique em **Add people**
3. Digite o nome de usuário ou e-mail do GitHub da pessoa
4. Selecione o nível de acesso:
   - **Read** — apenas visualizar
   - **Write** — visualizar e editar
   - **Admin** — controle total

A pessoa recebe um convite por e-mail e aceita com um clique.

---

## Alternativa mais simples: enviar o arquivo por e-mail

Se não quiser usar o GitHub agora, basta:

1. Enviar o arquivo `prototipo.html` por e-mail, WhatsApp ou Google Drive
2. O destinatário salva no computador e abre com qualquer navegador
3. Funciona 100% sem internet (exceto os ícones, que precisam de conexão)

---

## Próximos passos no desenvolvimento

Quando o time de desenvolvimento começar a trabalhar no sistema real:

1. Instalar o **Git** no computador: https://git-scm.com/downloads
2. Clonar o repositório:
   ```bash
   git clone https://github.com/SEU-NOME/sistema-contratos.git
   ```
3. Instalar as dependências do backend:
   ```bash
   cd modulo-01-clientes/backend
   pip install -r requirements.txt
   ```
4. Configurar o banco e subir a API:
   ```bash
   cp .env.example .env   # editar com as credenciais do PostgreSQL
   uvicorn app.main:app --reload
   ```

---

## Dúvidas frequentes

**O link some depois de um tempo?**
Não. O GitHub Pages é permanente enquanto o repositório existir.

**Posso deixar o repositório privado?**
Sim, mas o GitHub Pages gratuito exige repositório público.
Para repositórios privados com Pages, é necessário o plano GitHub Team (US$ 4/mês por usuário).

**Como atualizo o protótipo quando houver mudanças?**
Basta fazer upload do novo arquivo `prototipo.html` no repositório.
O GitHub Pages atualiza automaticamente em 1–2 minutos.
