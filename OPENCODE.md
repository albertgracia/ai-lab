# FILE: /opt/ai-lab/config/opencode/AI_LAB_CONTEXT.md

# AI-LAB CONTEXT

You are operating inside Albert's local AI-Lab infrastructure.

Always respond in Spanish unless explicitly requested otherwise.

## Environment

Main Linux node:
- Hostname: ubuntu-ialab
- IP: 192.168.1.30
- Project root: /opt/ai-lab

Windows GPU nodes:
- Gaming PC RX9070XT
  - IP: 192.168.1.50
  - Hostname: X870EAORUSPRO
  - SSH user: ailab
  - VRAM: 16 GB

- Gaming PC RX7900XT
  - IP: 192.168.1.60
  - Hostname: X870AORUSELITE
  - SSH user: ailab
  - VRAM: 20 GB

## Core services

Docker services:
- traefik
- qdrant
- open-webui
- ollama
- portainer

Runtime:
- runtime/state/system_state.py
- runtime/state/gpu_state.py
- runtime/llm/model_router.py
- runtime/llm/invoke.py

## Rules

Never invent files, ports, services, logs, or configuration.
Use runtime state as source of truth.
Prefer safe diagnostics before proposing changes.
Do not restart, delete, overwrite, or modify infrastructure without explicit confirmation.
Always distinguish FACT from HYPOTHESIS.
For code changes, explain target file and expected effect.
For infra changes, include rollback.


---

# FILE: /opt/ai-lab/config/opencode/POLICY.md

# OPENCODE POLICY FOR AI-LAB

## Language
Always answer in Spanish.

## Safety
Do not perform destructive changes automatically.
No rm -rf.
No docker compose down unless explicitly approved.
No systemctl restart unless explicitly approved.
No editing production configs without backup.
No secrets in logs.

## Reasoning
Use evidence from:
- system_state.py
- gpu_state.py
- docker inspect/logs
- git status
- current files

## Workflow
1. Understand request.
2. Inspect relevant files.
3. Build hypothesis.
4. Propose minimal change.
5. Validate.
6. Document result.

## Preferred output
- concise
- actionable
- command blocks
- explain risk
- include rollback when needed


---

# FILE: /opt/ai-lab/config/opencode/MODEL_STRATEGY.md

# MODEL STRATEGY

Default fast model:
- google/gemma-4-e4b

Reasoning model:
- qwen3-14b-claude-sonnet-4.5-reasoning-distill

Coding model:
- qwen2.5-coder-14b-instruct
- qwen2.5-coder-32b-instruct if enough VRAM

Embedding model:
- text-embedding-nomic-embed-text-v1.5

Vision:
- moondream2

Image:
- flux.2-klein-9b

Routing priorities:
1. Prefer online nodes.
2. Prefer models already loaded.
3. Prefer node with enough VRAM.
4. Prefer lower GPU usage.
5. Fallback to Main LM Studio.


---

# FILE: /opt/ai-lab/runtime/state/system_snapshot.json

{
  "docker": {
    "containers": [
      {
        "Command": "\"/entrypoint.sh --ap\u2026\"",
        "CreatedAt": "2026-05-09 15:10:18 +0000 UTC",
        "ID": "51e92b827907",
        "Image": "traefik:latest",
        "Labels": "com.docker.compose.config-hash=d7f80995e9ced71424becf4213a10ec5c26e62b796f82096017078b8ae159629,com.docker.compose.container-number=1,com.docker.compose.depends_on=,com.docker.compose.image=sha256:eb328e2c806c53aafbbace6c451fa54d268961261a85452fcf0fb752a30c17be,com.docker.compose.oneoff=False,com.docker.compose.project.config_files=/opt/ai-lab/stacks/traefik/docker-compose.yml,com.docker.compose.project.working_dir=/opt/ai-lab/stacks/traefik,com.docker.compose.project=traefik,com.docker.compose.replace=traefik,com.docker.compose.service=traefik,com.docker.compose.version=5.1.3,org.opencontainers.image.description=A modern reverse-proxy,org.opencontainers.image.documentation=https://docs.traefik.io,org.opencontainers.image.source=https://github.com/traefik/traefik,org.opencontainers.image.title=Traefik,org.opencontainers.image.url=https://traefik.io,org.opencontainers.image.vendor=Traefik Labs,org.opencontainers.image.version=v3.7.0",
        "LocalVolumes": "0",
        "Mounts": "/etc/localtime,/var/run/docke\u2026,/opt/ai-lab/da\u2026,/opt/ai-lab/da\u2026",
        "Names": "traefik",
        "Networks": "proxy",
        "Platform": {
          "architecture": "amd64",
          "os": "linux"
        },
        "Ports": "0.0.0.0:80->80/tcp, [::]:80->80/tcp, 0.0.0.0:443->443/tcp, [::]:443->443/tcp, 0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp",
        "RunningFor": "19 hours ago",
        "Size": "16.4kB (virtual 190MB)",
        "State": "running",
        "Status": "Up 32 minutes"
      },
      {
        "Command": "\"./entrypoint.sh\"",
        "CreatedAt": "2026-05-09 13:23:10 +0000 UTC",
        "ID": "f52f55e1fc86",
        "Image": "qdrant/qdrant:latest",
        "Labels": "com.docker.compose.config-hash=5c7f308ed1feecc6ed55d4cd92a3e0b9c251345982d513d41bcb2c5cbdd570e1,com.docker.compose.container-number=1,com.docker.compose.depends_on=,com.docker.compose.image=sha256:1cf3e07c9f269030c7cfed0d5c0beea7bb081848a88e2ae13b35a613d4dd5019,com.docker.compose.oneoff=False,com.docker.compose.project.config_files=/opt/ai-lab/stacks/qdrant/docker-compose.yml,com.docker.compose.project.working_dir=/opt/ai-lab/stacks/qdrant,com.docker.compose.project=qdrant,com.docker.compose.service=qdrant,com.docker.compose.version=5.1.3,org.opencontainers.image.description=Official Qdrant image,org.opencontainers.image.documentation=https://qdrant.com/docs,org.opencontainers.image.source=https://github.com/qdrant/qdrant,org.opencontainers.image.title=Qdrant,org.opencontainers.image.url=https://qdrant.com/,org.opencontainers.image.vendor=Qdrant,org.opencontainers.image.version=v1.18.0,traefik.enable=true,traefik.http.routers.qdrant.rule=Host(`qdrant.local`),traefik.http.services.qdrant.loadbalancer.server.port=6333",
        "LocalVolumes": "0",
        "Mounts": "/opt/ai-lab/da\u2026",
        "Names": "qdrant",
        "Networks": "proxy",
        "Platform": {
          "architecture": "amd64",
          "os": "linux"
        },
        "Ports": "0.0.0.0:6333-6334->6333-6334/tcp, [::]:6333-6334->6333-6334/tcp",
        "RunningFor": "21 hours ago",
        "Size": "24.6kB (virtual 199MB)",
        "State": "running",
        "Status": "Up 32 minutes"
      },
      {
        "Command": "\"bash start.sh\"",
        "CreatedAt": "2026-05-09 10:56:33 +0000 UTC",
        "ID": "6ad95129698d",
        "Image": "ghcr.io/open-webui/open-webui:main",
        "Labels": "com.docker.compose.config-hash=b2eb1af17ffcdd813b50c9a3fe2625f452555836326a0e5afb9efc2a1ff35b9e,com.docker.compose.container-number=1,com.docker.compose.depends_on=ollama:service_started:false,com.docker.compose.image=sha256:a6da0c292081d810a396ce786a10536d0b1b9ba2925dcca20ebb03f9fa90dbff,com.docker.compose.oneoff=False,com.docker.compose.project.config_files=/opt/ai-lab/stacks/ai-core/docker-compose.yml,com.docker.compose.project.working_dir=/opt/ai-lab/stacks/ai-core,com.docker.compose.project=ai-core,com.docker.compose.service=open-webui,com.docker.compose.version=5.1.3,org.opencontainers.image.created=2026-05-09T07:50:30.236Z,org.opencontainers.image.description=User-friendly AI Interface (Supports Ollama, OpenAI API, ...),org.opencontainers.image.licenses=NOASSERTION,org.opencontainers.image.revision=f51d2b026f1b0e7283b15f093412be8b67d24770,org.opencontainers.image.source=https://github.com/open-webui/open-webui,org.opencontainers.image.title=open-webui,org.opencontainers.image.url=https://github.com/open-webui/open-webui,org.opencontainers.image.version=main,traefik.enable=true,traefik.http.routers.openwebui.entrypoints=web,traefik.http.routers.openwebui.rule=Host(`openwebui.local`),traefik.http.services.openwebui.loadbalancer.server.port=8080",
        "LocalVolumes": "0",
        "Mounts": "/opt/ai-lab/da\u2026",
        "Names": "open-webui",
        "Networks": "proxy",
        "Platform": {
          "architecture": "amd64",
          "os": "linux"
        },
        "Ports": "0.0.0.0:3000->8080/tcp, [::]:3000->8080/tcp",
        "RunningFor": "23 hours ago",
        "Size": "54.3MB (virtual 5.04GB)",
        "State": "running",
        "Status": "Up 32 minutes (healthy)"
      },
      {
        "Command": "\"/bin/ollama serve\"",
        "CreatedAt": "2026-05-09 10:56:33 +0000 UTC",
        "ID": "76166a5eff6a",
        "Image": "ollama/ollama:latest",
        "Labels": "com.docker.compose.config-hash=89452da86d630ace97f090a3ead000c98adb9fa4aa3c8d6d36677db020b654c9,com.docker.compose.container-number=1,com.docker.compose.depends_on=,com.docker.compose.image=sha256:d00473cb58f0082c07cd6ed0d326a8a86f443ab69c51f8fc2b1a41687d45c661,com.docker.compose.oneoff=False,com.docker.compose.project.config_files=/opt/ai-lab/stacks/ai-core/docker-compose.yml,com.docker.compose.project.working_dir=/opt/ai-lab/stacks/ai-core,com.docker.compose.project=ai-core,com.docker.compose.service=ollama,com.docker.compose.version=5.1.3,org.opencontainers.image.version=24.04",
        "LocalVolumes": "0",
        "Mounts": "/mnt/ai-models\u2026",
        "Names": "ollama",
        "Networks": "proxy",
        "Platform": {
          "architecture": "amd64",
          "os": "linux"
        },
        "Ports": "0.0.0.0:11434->11434/tcp, [::]:11434->11434/tcp",
        "RunningFor": "23 hours ago",
        "Size": "16.4kB (virtual 6.56GB)",
        "State": "running",
        "Status": "Up 32 minutes"
      },
      {
        "Command": "\"/portainer\"",
        "CreatedAt": "2026-05-09 10:44:50 +0000 UTC",
        "ID": "84904750ef0a",
        "Image": "portainer/portainer-ce:latest",
        "Labels": "com.docker.compose.config-hash=ce5a79d75f29e29ccd685ad1fc5ae5aa7cc1082884660bbe2af954dd4e257d41,com.docker.compose.container-number=1,com.docker.compose.depends_on=,com.docker.compose.image=sha256:8d2f5c9fbc5b8490fb3a12efadbad74978e22991911e1db611d8a45871775112,com.docker.compose.oneoff=False,com.docker.compose.project.config_files=/opt/ai-lab/stacks/portainer/docker-compose.yml,com.docker.compose.project.working_dir=/opt/ai-lab/stacks/portainer,com.docker.compose.project=portainer,com.docker.compose.service=portainer,com.docker.compose.version=5.1.3,com.docker.desktop.extension.api.version=>= 0.2.2,com.docker.desktop.extension.icon=https://portainer-io-assets.sfo2.cdn.digitaloceanspaces.com/logos/portainer.png,com.docker.extension.additional-urls=[{\"title\":\"Website\",\"url\":\"https://www.portainer.io?utm_campaign=DockerCon&utm_source=DockerDesktop\"},{\"title\":\"Documentation\",\"url\":\"https://docs.portainer.io\"},{\"title\":\"Support\",\"url\":\"https://join.slack.com/t/portainer/shared_invite/zt-txh3ljab-52QHTyjCqbe5RibC2lcjKA\"}],com.docker.extension.detailed-description=<p data-renderer-start-pos=\"226\">Portainer&rsquo;s Docker Desktop extension gives you access to all of Portainer&rsquo;s rich management functionality within your docker desktop experience.</p><h2 data-renderer-start-pos=\"374\">With Portainer you can:</h2><ul><li>See all your running containers</li><li>Easily view all of your container logs</li><li>Console into containers</li><li>Easily deploy your code into containers using a simple form</li><li>Turn your YAML into custom templates for easy reuse</li></ul><h2 data-renderer-start-pos=\"660\">About Portainer&nbsp;</h2><p data-renderer-start-pos=\"680\">Portainer is the worlds&rsquo; most popular universal container management platform with more than 650,000 active monthly users. Portainer can be used to manage Docker Standalone, Kubernetes and Docker Swarm environments through a single common interface. It includes a simple GitOps automation engine and a Kube API.&nbsp;</p><p data-renderer-start-pos=\"1006\">Portainer Business Edition is our fully supported commercial grade product for business-wide use. It includes all the functionality that businesses need to manage containers at scale. Visit <a class=\"sc-jKJlTe dPfAtb\" href=\"http://portainer.io/\" title=\"http://Portainer.io\" data-renderer-mark=\"true\">Portainer.io</a> to learn more about Portainer Business and <a class=\"sc-jKJlTe dPfAtb\" href=\"http://portainer.io/take-3?utm_campaign=DockerCon&amp;utm_source=Docker%20Desktop\" title=\"http://portainer.io/take-3?utm_campaign=DockerCon&amp;utm_source=Docker%20Desktop\" data-renderer-mark=\"true\">get 3 free nodes.</a></p>,com.docker.extension.publisher-url=https://www.portainer.io,com.docker.extension.screenshots=[{\"alt\": \"screenshot one\", \"url\": \"https://portainer-io-assets.sfo2.digitaloceanspaces.com/screenshots/docker-extension-1.png\"},{\"alt\": \"screenshot two\", \"url\": \"https://portainer-io-assets.sfo2.digitaloceanspaces.com/screenshots/docker-extension-2.png\"},{\"alt\": \"screenshot three\", \"url\": \"https://portainer-io-assets.sfo2.digitaloceanspaces.com/screenshots/docker-extension-3.png\"},{\"alt\": \"screenshot four\", \"url\": \"https://portainer-io-assets.sfo2.digitaloceanspaces.com/screenshots/docker-extension-4.png\"},{\"alt\": \"screenshot five\", \"url\": \"https://portainer-io-assets.sfo2.digitaloceanspaces.com/screenshots/docker-extension-5.png\"},{\"alt\": \"screenshot six\", \"url\": \"https://portainer-io-assets.sfo2.digitaloceanspaces.com/screenshots/docker-extension-6.png\"},{\"alt\": \"screenshot seven\", \"url\": \"https://portainer-io-assets.sfo2.digitaloceanspaces.com/screenshots/docker-extension-7.png\"},{\"alt\": \"screenshot eight\", \"url\": \"https://portainer-io-assets.sfo2.digitaloceanspaces.com/screenshots/docker-extension-8.png\"},{\"alt\": \"screenshot nine\", \"url\": \"https://portainer-io-assets.sfo2.digitaloceanspaces.com/screenshots/docker-extension-9.png\"}],git_commit=ece7e56,io.portainer.server=true,org.opencontainers.image.created=2026-05-07T02:58:10Z,org.opencontainers.image.description=Portainer Community Edition server.,org.opencontainers.image.documentation=https://docs.portainer.io,org.opencontainers.image.revision=ece7e56,org.opencontainers.image.title=Portainer CE,org.opencontainers.image.url=https://www.portainer.io,org.opencontainers.image.vendor=Portainer.io,traefik.enable=true,traefik.http.routers.portainer.entrypoints=web,traefik.http.routers.portainer.rule=Host(`portainer.local`),traefik.http.services.portainer.loadbalancer.server.port=9000",
        "LocalVolumes": "0",
        "Mounts": "/opt/ai-lab/da\u2026,/var/run/docke\u2026",
        "Names": "portainer",
        "Networks": "proxy",
        "Platform": {
          "architecture": "amd64",
          "os": "linux"
        },
        "Ports": "8000/tcp, 9443/tcp, 0.0.0.0:9000->9000/tcp, [::]:9000->9000/tcp",
        "RunningFor": "23 hours ago",
        "Size": "16.4kB (virtual 182MB)",
        "State": "running",
        "Status": "Up 32 minutes"
      }
    ]
  },
  "llm": {
    "lmstudio_nodes": [
      {
        "node": "Main LM Studio",
        "online": true,
        "models": [
          "google/gemma-4-e4b",
          "text-embedding-nomic-embed-text-v1.5"
        ]
      },
      {
        "node": "Gaming PC RX7900XT",
        "online": false,
        "error": "HTTPConnectionPool(host='192.168.1.60', port=1234): Max retries exceeded with url: /v1/models (Caused by NewConnectionError(\"HTTPConnection(host='192.168.1.60', port=1234): Failed to establish a new connection: [Errno 113] No route to host\"))"
      },
      {
        "node": "Gaming PC RX9070XT",
        "online": true,
        "models": [
          "text-embedding-nomic-embed-text-v1.5"
        ]
      }
    ]
  },
  "gpu": [
    {
      "node": "Gaming PC RX9070XT",
      "host": "192.168.1.50",
      "gpu_usage": {
        "max_gpu_usage_percent": 0.05,
        "active_engines": [
          {
            "path": "\\\\X870EAORUSPRO\\GPU Engine(pid_1192_luid_0x00000000_0x0001A54E_phys_0_eng_0_engtype_3D)\\Utilization Percentage",
            "value": 0.048941
          },
          {
            "path": "\\\\X870EAORUSPRO\\GPU Engine(pid_17384_luid_0x00000000_0x0001A54E_phys_0_eng_0_engtype_3D)\\Utilization Percentage",
            "value": 0.034092
          }
        ]
      },
      "vram": {
        "vram_used_gib": 2.31,
        "vram_total_gib": 16,
        "vram_free_gib_estimated": 13.69,
        "raw_samples": [
          {
            "path": "\\\\X870EAORUSPRO\\GPU Adapter Memory(luid_0x00000000_0x0001A54E_phys_0)\\Dedicated Usage",
            "value": 2479771648.0
          },
          {
            "path": "\\\\X870EAORUSPRO\\GPU Adapter Memory(luid_0x00000000_0x0001D764_phys_0)\\Dedicated Usage",
            "value": 0.0
          }
        ]
      }
    },
    {
      "node": "Gaming PC RX7900XT",
      "host": "192.168.1.60",
      "gpu_usage": {
        "error": "ssh: connect to host 192.168.1.60 port 22: No route to host"
      },
      "vram": {
        "error": "ssh: connect to host 192.168.1.60 port 22: No route to host"
      }
    }
  ]
}
