# 01 — System context

Diagrams follow the [C4 model](https://c4model.com/). They are Mermaid, so GitHub renders them.

## Level 1: system context

```mermaid
flowchart LR
    seller([Seller])
    curator([Curator / admin])
    shop[(Seller's storefront<br/>Shopify / Instagram / marketplace)]
    hf[(Hugging Face<br/>model weights)]
    gpu[[GPU provider<br/>Kaggle / Colab / local → Modal / RunPod]]

    subgraph sys[TryOn App]
      app[Web app + API + storage]
    end

    seller -- uploads garments, downloads photos --> app
    curator -- approves house models & poses --> app
    seller -- publishes photos --> shop
    app -- jobs --> gpu
    gpu -- loads weights --> hf
```

## Level 2: containers

```mermaid
flowchart TB
    browser([Browser])

    subgraph cf[Cloudflare]
      web[Web app<br/>React + Vite<br/>Pages]
      api[API<br/>FastAPI<br/>Containers / Python Workers]
      d1[(D1<br/>metadata + job table)]
      r2[(R2<br/>images)]
      q[[Queues<br/>v1 only]]
    end

    subgraph gpu[GPU runtime]
      worker[Worker<br/>Python + engine package]
      weights[(Model cache)]
    end

    browser -->|HTTPS| web
    browser -->|JSON over HTTPS| api
    browser -->|presigned PUT/GET| r2
    api --> d1
    api -->|presign| r2
    api -.->|v1 push| q
    worker -->|lease / heartbeat / complete<br/>HTTPS + worker token| api
    worker -->|presigned GET/PUT| r2
    q -.->|v1| worker
    worker --> weights
```

### Notes

- **Images never pass through the API.** Browser and worker read and write R2 directly with short-lived presigned URLs. The API only handles small JSON. This keeps the API inside Cloudflare's request and CPU limits.
- **The worker only makes outbound calls.** It needs no public IP or inbound port, which is why free notebooks and a home PC can act as workers.
- **D1 is the job queue in v0** (lease columns on the `job` table). Cloudflare Queues are added only when push-based serverless GPUs arrive (see [ADR-0002](adr/0002-pull-based-gpu-worker.md)).

## Main user flow (sequence)

```mermaid
sequenceDiagram
    actor S as Seller
    participant W as Web
    participant A as API
    participant R as R2
    participant G as GPU worker

    S->>W: Choose garment photos (front, back), category
    W->>A: POST /v1/garments
    A-->>W: garment_id + presigned PUT URLs
    W->>R: PUT front.jpg, back.jpg
    W->>A: POST /v1/garments/{id}/uploaded
    A->>A: validate, status = ready
    S->>W: Pick house model + angles
    W->>A: POST /v1/jobs
    A-->>W: job_id (queued)
    loop every few seconds
      G->>A: POST /v1/worker/lease
    end
    A-->>G: job + presigned GET/PUT URLs
    G->>R: GET garment + base images
    G->>G: segment → swap → rank → post-process
    G->>R: PUT candidates
    G->>A: POST /v1/worker/jobs/{id}/complete (scores)
    W->>A: GET /v1/jobs/{id} (poll)
    A-->>W: succeeded + result URLs
    S->>W: Pick favourites, download ZIP
```
