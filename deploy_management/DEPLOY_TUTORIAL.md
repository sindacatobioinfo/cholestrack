# Tutorial de Deploy: Nginx, Gunicorn e Celery

Este tutorial descreve como configurar o ambiente de produção para o projeto **Cholestrack** utilizando Nginx como servidor web (reverse proxy), Gunicorn como servidor de aplicação WSGI, e Celery para tarefas em segundo plano.

O guia baseia-se nos arquivos de configuração encontrados em `deploy_management/` e no script `/cholestrack/gunicorn-start.sh`.

## Pré-requisitos

*   Servidor Linux (Ubuntu/Debian recomendado).
*   Acesso root ou sudo.
*   Projeto localizado em `/home/burlo/cholestrack/`.
*   Virtualenv criada em `/home/burlo/cholestrack/cholestrack/.venv/`.
*   Usuário do sistema: `burlo`.

---

## 1. Configuração do Gunicorn

O Gunicorn serve a aplicação Django. Existem duas formas de iniciá-lo baseadas nos arquivos do projeto: via script shell ou via serviço Systemd (recomendado para produção).

### Opção A: Serviço Systemd (Recomendado)

O arquivo `deploy_management/gunicorn.service` define como o Gunicorn deve rodar e reiniciar automaticamente.

1.  **Copie o arquivo de serviço para o systemd:**
    ```bash
    sudo cp /home/burlo/cholestrack/deploy_management/gunicorn.service /etc/systemd/system/
    ```

2.  **Inicie e habilite o serviço:**
    ```bash
    sudo systemctl start gunicorn
    sudo systemctl enable gunicorn
    ```

3.  **Verifique o status:**
    ```bash
    sudo systemctl status gunicorn
    ```

### Opção B: Script Manual (`gunicorn-start.sh`)

O arquivo `/cholestrack/gunicorn-start.sh` é um script wrapper útil para testar a execução ou se você preferir não usar o systemd diretamente para o processo (embora menos robusto).

1.  **Dê permissão de execução:**
    ```bash
    chmod +x /home/burlo/cholestrack/cholestrack/gunicorn-start.sh
    ```

2.  **Execute:**
    ```bash
    ./home/burlo/cholestrack/cholestrack/gunicorn-start.sh
    ```

---

## 2. Configuração do Celery (Background Workers)

O Celery é dividido em dois serviços: o **Worker** (processa tarefas) e o **Beat** (agendamento).

### Configurar Diretórios de Log
Os arquivos `.service` referenciam diretórios de log e PID que precisam existir.

```bash
# Criação de diretórios para logs e pids
sudo mkdir -p /var/log/celery /var/run/celery
sudo chown -R burlo:burlo /var/log/celery /var/run/celery
```

### Instalar Serviços

1.  **Copie os arquivos de serviço:**
    ```bash
    sudo cp /home/burlo/cholestrack/deploy_management/celery.service /etc/systemd/system/
    sudo cp /home/burlo/cholestrack/deploy_management/celerybeat.service /etc/systemd/system/
    ```

2.  **Recarregue o daemon do systemd:**
    ```bash
    sudo systemctl daemon-reload
    ```

3.  **Inicie e habilite os serviços:**
    ```bash
    sudo systemctl start celery
    sudo systemctl start celerybeat
    sudo systemctl enable celery
    sudo systemctl enable celerybeat
    ```

---

## 3. Configuração do Nginx

O Nginx atua como porta de entrada, servindo arquivos estáticos/media e repassando requisições dinâmicas para o Gunicorn via socket.

1.  **Instale o Nginx (se não estiver instalado):**
    ```bash
    sudo apt-get update
    sudo apt-get install nginx
    ```

2.  **Configuração do Site:**
    O arquivo `deploy_management/cholestrack` contém a configuração do bloco de servidor (Server Block).

    Copie-o para os sites disponíveis e crie o link simbólico:
    ```bash
    sudo cp /home/burlo/cholestrack/deploy_management/cholestrack /etc/nginx/sites-available/cholestrack
    sudo ln -s /etc/nginx/sites-available/cholestrack /etc/nginx/sites-enabled/
    ```

3.  **Configuração Geral (Opcional):**
    O arquivo `deploy_management/nginx.conf` contém configurações globais otimizadas. Se desejar usar estas configurações globais:
    ```bash
    sudo cp /home/burlo/cholestrack/deploy_management/nginx.conf /etc/nginx/nginx.conf
    ```

4.  **Teste e Reinicie:**
    ```bash
    sudo nginx -t
    sudo systemctl restart nginx
    ```

---

## 4. Adicionando um Custom Domain (Domínio Personalizado)

Para acessar o site através de um domínio próprio (ex: `meusite.com.br`) ao invés do IP, siga estes passos:

### Passo 1: Configuração de DNS
No painel de controle onde você comprou o domínio (GoDaddy, Registro.br, Route53, etc.), crie um registro do tipo **A**:
*   **Name/Host:** `@` (e/ou `www`)
*   **Value/Target:** O endereço IP Público do seu servidor VPS.

### Passo 2: Atualizar o Nginx
Edite o arquivo de configuração do site no servidor:

```bash
sudo nano /etc/nginx/sites-available/cholestrack
```

Encontre as linhas `server_name _;` (existem duas, uma para porta 80 e outra para 443) e altere para o seu domínio:

**Antes:**
```nginx
server_name _;
```

**Depois:**
```nginx
server_name meusite.com.br www.meusite.com.br;
```

Faça isso tanto no bloco `listen 80` quanto no `listen 443`.

### Passo 3: Configurar HTTPS (SSL)
O arquivo de configuração atual aponta para certificados manuais em `/etc/nginx/ssl/cholestrack.crt`. Ao usar um domínio real, a maneira mais fácil e segura de obter HTTPS gratuito é usando o **Certbot (Let's Encrypt)**.

1.  **Instale o Certbot:**
    ```bash
    sudo apt-get install certbot python3-certbot-nginx
    ```

2.  **Gere o certificado:**
    O Certbot irá ler seu `server_name`, gerar os certificados e atualizar o arquivo do Nginx automaticamente.
    ```bash
    sudo certbot --nginx -d meusite.com.br -d www.meusite.com.br
    ```

3.  **Reinicie o Nginx:**
    ```bash
    sudo systemctl restart nginx
    ```

Agora seu site estará acessível via `https://meusite.com.br`.

---

## Resumo de Comandos Úteis

| Ação | Comando |
|------|---------|
| Ver status Gunicorn | `sudo systemctl status gunicorn` |
| Ver status Celery | `sudo systemctl status celery` |
| Ver logs Nginx (Acesso) | `tail -f /home/burlo/cholestrack/deploy_management/logs/nginx-access.log` |
| Ver logs Nginx (Erro) | `tail -f /home/burlo/cholestrack/deploy_management/logs/nginx-error.log` |
| Reiniciar tudo | `sudo systemctl restart gunicorn celery celerybeat nginx` |
