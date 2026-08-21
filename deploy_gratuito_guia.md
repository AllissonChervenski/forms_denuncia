# 🚀 Guia de Produção e Hospedagem 100% Gratuita (Oracle Cloud Always Free)

Este manual fornece o passo a passo completo para hospedar o projeto **forms_denuncia** em ambiente de produção com **custo zero permanente**, utilizando a infraestrutura **Always Free da Oracle Cloud (OCI)** com orquestração completa via **Docker Compose**, **Nginx (SSL/HTTPS Grátis)**, **PostgreSQL 16**, **Redis 7**, **Celery Worker** (com compressão automática de fotos) e **Deploy Contínuo via GitHub Actions**.

---

## 📋 Índice

1. [Por que a Oracle Cloud Always Free?](#1-por-que-a-oracle-cloud-always-free)
2. [Passo 1: Criação da Conta e Provisionamento da VPS](#passo-1-criação-da-conta-e-provisionamento-da-vps)
3. [Passo 2: Configuração de Rede e Portas (VCN & Firewall)](#passo-2-configuração-de-rede-e-portas-vcn--firewall)
4. [Passo 3: Instalação do Docker e Preparação do Servidor](#passo-3-instalação-do-docker-e-preparação-do-servidor)
5. [Passo 4: Configuração de Domínio e Certificado SSL Grátis](#passo-4-configuração-de-domínio-e-certificado-ssl-grátis)
6. [Passo 5: Configuração das Variáveis de Ambiente](#passo-5-configuração-das-variáveis-de-ambiente)
7. [Passo 6: Automação do Deploy via GitHub Actions](#passo-6-automação-do-deploy-via-github-actions)
8. [Passo 7: Verificação do Sistema e Compressão de Imagens](#passo-7-verificação-do-sistema-e-compressão-de-imagens)
9. [Passo 8: Manutenção, Logs e Backup Gratuito](#passo-8-manutenção-logs-e-backup-gratuito)

---

## 1. Por que a Oracle Cloud Always Free?

A Oracle Cloud oferece a camada gratuita mais generosa e robusta da indústria de computação em nuvem:

* **Hardware Gratuito Permanente:**
  * **Opção ARM Ampere:** Até **4 OCPUs (núcleos)** e **24 GB de Memória RAM** (podendo ser dividida em até 4 instâncias ou 1 instância grande).
  * **Opção AMD:** 2 instâncias micro (*1 vCPU, 1 GB de RAM* cada).
  * **Armazenamento:** **200 GB** de disco em bloco NVMe gratuito permanente.
  * **Tráfego:** **10 TB/mês** de transferência de dados de saída gratuita.
* **Sem Hibernação (Sem Sleep):** Diferente de PaaS gratuitas (como Render ou Railway), o servidor permanece **online 24/7/365** com resposta instantânea.
* **Compatibilidade Nativa:** Executa diretamente o nosso `docker-compose.prod.yml` com todos os 6 containers integrados em rede isolada.

---

## Passo 1: Criação da Conta e Provisionamento da VPS

1. Acesse o site oficial: [oracle.com/cloud/free](https://www.oracle.com/cloud/free/) e clique em **Start for free**.
2. Preencha seus dados cadastrais. *(Nota: Será solicitado um cartão de crédito para validação anti-fraude, mas nenhum valor será cobrado no modo Always Free)*.
3. No painel da Oracle Cloud (Console OCI), selecione o menu:
   **Compute > Instances > Create Instance**.
4. Configure a instância:
   * **Name:** `forms-denuncia-prod`
   * **Placement:** Deixe a Availability Domain padrão.
   * **Image and Shape:**
     * **Image:** `Ubuntu 24.04 LTS` ou `Ubuntu 22.04 LTS (Canonical Ubuntu)`
     * **Shape:** Clique em *Change Shape* > Selecione **Ampere (ARM)** > Configure **2 OCPUs** e **12 GB de RAM** *(ou Shape AMD Micro padrão se ARM estiver sem cota na sua região)*.
   * **Networking:** Crie uma nova VCN (Virtual Cloud Network) e marque a opção **Assign a public IPv4 address**.
   * **Add SSH Keys:** Selecione **Generate a key pair for me** e faça o download obrigatório da **Private Key** (arquivo `.key`). Guarde esta chave com segurança!
   * **Boot Volume:** Deixe o padrão (50 GB a 100 GB).
5. Clique em **Create**. Em cerca de 1 minuto, a VPS estará com status **Running** e exibirá seu **Public IP Address** (ex: `129.148.x.x`).

---

## Passo 2: Configuração de Rede e Portas (VCN & Firewall)

### 1. Liberar portas no Painel da Oracle (Security List da VCN)
1. Na página da sua instância, clique no link da sua **Subnet**.
2. Clique na **Default Security List**.
3. Clique em **Add Ingress Rules** e adicione:
   * **Source CIDR:** `0.0.0.0/0`
   * **IP Protocol:** `TCP`
   * **Destination Port Range:** `80,443`
   * **Description:** `HTTP and HTTPS for forms_denuncia`
4. Clique em **Add Ingress Rules**.

### 2. Liberar portas no Firewall do Ubuntu (IPTables / UFW)
Conecte-se via terminal à sua VPS utilizando a chave SSH baixada:
```bash
chmod 400 ssh-key-*.key
ssh -i ssh-key-*.key ubuntu@<SEU_IP_PUBLICO>
```

Execute os comandos para ajustar o firewall interno do Ubuntu:
```bash
# Atualiza regras do iptables para permitir tráfego web
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save 2>/dev/null || true

# Configura e ativa o UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

---

## Passo 3: Instalação do Docker e Preparação do Servidor

Dentro da VPS, instale o Docker e o Docker Compose oficial com um único script:

```bash
# Atualizar repositórios do sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker Engine oficial
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Instalar utilitários essenciais
sudo apt install -y git curl certbot

# Ativar o grupo docker sem reiniciar
newgrp docker
```

Teste se o Docker está funcionando:
```bash
docker --version && docker compose version
```

---

## Passo 4: Configuração de Domínio e Certificado SSL Grátis

### 1. Obter um Domínio Gratuito (Ex: DuckDNS ou Cloudflare)
Se não possuir um domínio próprio (ex: `.com.br`):
1. Acesse [duckdns.org](https://www.duckdns.org) e faça login com GitHub.
2. Crie um subdomínio gratuito, ex: `denuncias-cerest.duckdns.org`.
3. Aponte o IP do subdomínio para o **IP público** da sua VPS da Oracle.

### 2. Gerar Certificado SSL Grátis com Let's Encrypt (Certbot)
Para obter HTTPS com cadeado verde:
```bash
sudo certbot certonly --standalone -d seu-dominio.duckdns.org --non-interactive --agree-tos -m seu-email@exemplo.com
```
Os certificados serão salvos em `/etc/letsencrypt/live/seu-dominio.duckdns.org/`.

---

## Passo 5: Configuração das Variáveis de Ambiente

Na VPS, prepare o diretório do projeto:

```bash
# Clonar o repositório
cd /home/ubuntu
git clone https://github.com/allissonchervenski/forms_denuncia.git
cd forms_denuncia

# Criar o arquivo de ambiente de produção
cp .env.production.example .env
```

Edite o arquivo `.env`:
```bash
nano .env
```

Preencha com dados seguros de produção:
```ini
DEBUG=False
SECRET_KEY=gere_uma_chave_longa_com_python_secrets
ALLOWED_HOSTS=seu-dominio.duckdns.org,127.0.0.1,<SEU_IP_PUBLICO>
CSRF_TRUSTED_ORIGINS=https://seu-dominio.duckdns.org,http://seu-dominio.duckdns.org

POSTGRES_DB=forms_denuncia_prod
POSTGRES_USER=forms_admin
POSTGRES_PASSWORD=defina_uma_senha_muito_forte_aqui
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/1
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

RATE_LIMIT_ENABLED=True
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

IMAGE_NAME=ghcr.io/seu-usuario-github/forms_denuncia
IMAGE_TAG=latest
```

---

## Passo 6: Automação do Deploy via GitHub Actions

Para que o deploy ocorra de forma **100% automatizada** a cada commit na branch `main` ou criação de tag de release:

1. No seu repositório no GitHub, acesse:
   **Settings > Secrets and variables > Actions > New repository secret**.
2. Cadastre os seguintes segredos:

| Secret Name | Valor |
| :--- | :--- |
| `PROD_HOST` | O IP público da sua VPS da Oracle (ex: `129.148.x.x`) |
| `PROD_USER` | `ubuntu` |
| `PROD_SSH_KEY` | Todo o conteúdo da chave privada SSH (`ssh-key-*.key`) |
| `PROD_PORT` | `22` |

3. Pronto! Ao realizar um `git push` para `main`, o GitHub Actions irá:
   - Executar os **74 testes automatizados** com PostgreSQL e Redis.
   - Varrer o código contra **segredos e chaves expostas** (`detect-secrets`) e vulnerabilidades (`bandit`).
   - Construir a imagem Docker multi-stage otimizada e publicar no **GitHub Packages (`ghcr.io`)**.
   - Conectar via SSH na sua VPS da Oracle e rodar o script [scripts/deploy.sh](scripts/deploy.sh) com zero downtime!

---

## Passo 7: Verificação do Sistema e Compressão de Imagens

### 1. Subir os serviços pela primeira vez na VPS:
```bash
./scripts/deploy.sh
```

### 2. Criar o usuário Gestor do Dashboard:
```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py createsuperuser
```

### 3. Teste do Fluxo de Compressão de Imagens:
1. Acesse `http://seu-dominio.duckdns.org/` e envie uma denúncia anexando uma foto pesada (ex: foto de celular de 10 MB).
2. Verifique os logs do Celery em tempo real:
   ```bash
   docker compose -f docker-compose.prod.yml logs -f celery
   ```
3. Você verá o log informando a redução drástica do tamanho:
   ```text
   [INFO] SUCESSO: EXIF limpo e imagem comprimida para evidência #1 (10240.0 KB -> 420.5 KB, economia: 95.9%)
   ```
4. A imagem estará perfeitamente visível e nítida no Dashboard (`/dashboard/`) sem consumir espaço excessivo.

---

## Passo 8: Manutenção, Logs e Backup Gratuito

### Visualizar Logs em Tempo Real
```bash
# Logs do Django/Gunicorn
docker compose -f docker-compose.prod.yml logs -f web

# Logs do Nginx
docker compose -f docker-compose.prod.yml logs -f nginx

# Status dos containers e uso de memória
docker stats
```

### Backup Automático Gratuito do PostgreSQL
Crie uma rotina diária simples no crontab da VPS:
```bash
crontab -e
```
Adicione a linha para gerar backup diário compactado às 03:00 da manhã:
```cron
0 3 * * * docker compose -f /home/ubuntu/forms_denuncia/docker-compose.prod.yml exec -T db pg_dump -U forms_admin forms_denuncia_prod | gzip > /home/ubuntu/backups/db_$(date +\%Y\%m\%d).sql.gz
```

---

## 🎯 Conclusão

Com esta arquitetura:
* Sua aplicação opera **24 horas por dia sem limites de tempo ou hibernação**.
* As fotos de denúncias são **comprimidas automaticamente pelo Celery**, economizando até 90% do disco.
* Todas as atualizações de código passam por testes e são publicadas de forma **segura e automática via GitHub Actions**.
* O custo total mensal é **R$ 0,00**.
