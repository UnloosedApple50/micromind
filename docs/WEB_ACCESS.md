# Guia de Acesso Web — MicroMind

> Como acessar a interface web do MicroMind de qualquer lugar do mundo

## Pré-requisitos

1. **O servidor MicroMind deve estar rodando** (no Mac ou servidor)
2. **Cloudflare Tunnel ativo** (para acesso externo)

## Passo a Passo

### 1. Iniciar o MicroMind

```bash
cd ~/Documents/micromind
source .venv/bin/activate
python3 -m uvicorn micromind.web.server:app --host 0.0.0.0 --port 8081
```

### 2. Criar o Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:8081
```

Isso vai gerar uma URL como:
```
https://xxx-yyy-zzz.trycloudflare.com
```

### 3. Acessar a Interface

Abra a URL gerada no navegador:
```
https://xxx-yyy-zzz.trycloudflare.com
```

## Funcionalidades da Interface

| Módulo | Função |
|--------|--------|
| **Dashboard** | Visão geral do sistema |
| **Contactos** | Criar e listar contactos |
| **Tarefas** | Criar e listar tarefas |
| **Tickets** | Criar e listar tickets |
| **MicroAI** | Classificação de intenções |
| **Automação** | Regras WHEN/IF/THEN |
| **Telefonia** | Simulação de chamadas |
| **Doctor** | Diagnóstico do Sistema |

## Para Administradores

### Criar um Tunnel Permanente (com conta Cloudflare)

1. Crie uma conta em https://cloudflare.com
2. Instale o cloudflared:
   ```bash
   brew install cloudflared
   ```
3. Autentique:
   ```bash
   cloudflared tunnel login
   ```
4. Crie um tunnel nomeado:
   ```bash
   cloudflared tunnel create micromind
   cloudflared tunnel route dns micromind micromind.seudominio.com
   cloudflared tunnel run micromind
   ```

### Acesso via IP Fixo (VPS)

Se tiver um VPS com IP fixo:
```bash
# No VPS
ssh usuario@ip_fixo
cd micromind
source .venv/bin/activate
python3 -m uvicorn micromind.web.server:app --host 0.0.0.0 --port 8081
```

Acesse: `http://IP_FIXO:8081`

## Resolução de Problemas

| Problema | Solução |
|----------|---------|
| "Connection refused" | Verifique se o servidor está rodando |
| "Tunnel not found" | Recrie o tunnel com `cloudflared tunnel --url http://localhost:8081` |
| "jinja2 not found" | Execute `pip install jinja2` |
| "Port 8081 in use" | Use outra porta: `--port 8082` |

## Segurança

- O MicroMind roda em **Safe Mode** por padrão
- Nenhuma chamada real é feita sem configuração explícita
- Nenhum email real é enviado sem autorização
- Todos os dados ficam armazenados localmente

## Suporte

- **GitHub:** https://github.com/UnloosedApple50/micromind
- **Documentação:** `docs/`
- **Testes:** `pytest tests/ -v`
