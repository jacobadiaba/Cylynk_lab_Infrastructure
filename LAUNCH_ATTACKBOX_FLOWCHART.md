# AttackBox Launch Flow

This document describes the complete flow when a student clicks "Launch AttackBox" in the Moodle plugin.

---

## High-Level Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Student   │────▶│   Moodle    │────▶│ API Gateway │────▶│   Lambda    │
│   Browser   │     │   Plugin    │     │             │     │  Functions  │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                    │
                    ┌───────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  DynamoDB   │◀───▶│ Auto Scaling│◀───▶│     EC2     │◀───▶│  Guacamole  │
│   Tables    │     │   Groups    │     │  Instances  │     │   Server    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## Detailed Flowchart

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        STUDENT CLICKS "LAUNCH ATTACKBOX"                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MOODLE PLUGIN (launcher.js)                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│  1. Check if student has existing active session                                 │
│  2. Get student's plan tier (freemium/starter/pro) from Moodle                  │
│  3. Show loading modal with progress bar                                         │
│  4. Call API: POST /sessions                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY (HTTP API)                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  • Validate request                                                              │
│  • Check CORS (allowed origins)                                                  │
│  • Route to create-session Lambda                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CREATE-SESSION LAMBDA                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 1: Validate Request                                                   │ │
│  │  • Check required fields (student_id, student_name, course_id)            │ │
│  │  • Extract plan tier (default: "pro")                                     │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 2: Check Existing Session                                             │ │
│  │  • Query DynamoDB Sessions table by student_id                            │ │
│  │  • If ACTIVE/PROVISIONING session exists → Return existing session        │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                         ┌──────────────┴──────────────┐                         │
│                         │                             │                         │
│                         ▼                             ▼                         │
│              ┌─────────────────────┐      ┌─────────────────────┐              │
│              │ Existing Session    │      │ No Existing Session │              │
│              │ Return it           │      │ Continue...         │              │
│              └─────────────────────┘      └──────────┬──────────┘              │
│                                                      │                          │
│                                                      ▼                          │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 3: Determine ASG Based on Plan Tier                                   │ │
│  │                                                                            │ │
│  │   plan = "freemium" → ASG: cyberlab-dev-attackbox-freemium-pool           │ │
│  │   plan = "starter"  → ASG: cyberlab-dev-attackbox-starter-pool            │ │
│  │   plan = "pro"      → ASG: cyberlab-dev-attackbox-pro-pool                │ │
│  │                                                                            │ │
│  │   Instance Types:                                                          │ │
│  │   • Freemium: t3.small  (2 vCPU, 2GB RAM)                                 │ │
│  │   • Starter:  t3.medium (2 vCPU, 4GB RAM)                                 │ │
│  │   • Pro:      t3.large  (2 vCPU, 8GB RAM)                                 │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 4: Try to Find Available Instance                                     │ │
│  │                                                                            │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 4a. Query Instance Pool (DynamoDB)                                   │ │ │
│  │  │     • Filter: status = "AVAILABLE" AND plan = {student_plan}         │ │ │
│  │  └──────────────────────────────────────────────────────────────────────┘ │ │
│  │                              │                                            │ │
│  │              ┌───────────────┴───────────────┐                            │ │
│  │              │                               │                            │ │
│  │              ▼                               ▼                            │ │
│  │   ┌─────────────────────┐       ┌─────────────────────────────────┐      │ │
│  │   │ Found AVAILABLE     │       │ No AVAILABLE Instance           │      │ │
│  │   │ Instance            │       │                                 │      │ │
│  │   └──────────┬──────────┘       └────────────────┬────────────────┘      │ │
│  │              │                                   │                        │ │
│  │              ▼                                   ▼                        │ │
│  │   ┌─────────────────────┐       ┌─────────────────────────────────┐      │ │
│  │   │ Verify EC2 state    │       │ 4b. Check ASG for Running       │      │ │
│  │   │ is "running"        │       │     Instances directly          │      │ │
│  │   └──────────┬──────────┘       └────────────────┬────────────────┘      │ │
│  │              │                                   │                        │ │
│  │              ▼                                   ▼                        │ │
│  │   ┌─────────────────────┐       ┌─────────────────────────────────┐      │ │
│  │   │ Atomic claim with   │       │ For each instance in ASG:       │      │ │
│  │   │ DynamoDB conditional│       │  • Check if running + healthy   │      │ │
│  │   │ update              │       │  • Check pool record status     │      │ │
│  │   │                     │       │  • If unassigned → claim it     │      │ │
│  │   │ status: AVAILABLE   │       │  • If assigned to dead session  │      │ │
│  │   │      → ASSIGNED     │       │    → reclaim it                 │      │ │
│  │   └──────────┬──────────┘       └────────────────┬────────────────┘      │ │
│  │              │                                   │                        │ │
│  │              └───────────────┬───────────────────┘                        │ │
│  │                              │                                            │ │
│  │              ┌───────────────┴───────────────┐                            │ │
│  │              │                               │                            │ │
│  │              ▼                               ▼                            │ │
│  │   ┌─────────────────────┐       ┌─────────────────────────────────┐      │ │
│  │   │ Instance Claimed!   │       │ No Instance Available           │      │ │
│  │   │ Skip to Step 6      │       │ Go to Step 5                    │      │ │
│  │   └─────────────────────┘       └─────────────────────────────────┘      │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 5: Request Instance from Warm Pool / Scale Up                         │ │
│  │                                                                            │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ Check ASG capacity:                                                  │ │ │
│  │  │  • current_desired < max_capacity?                                   │ │ │
│  │  │  • If YES → set_desired_capacity(current + 1)                       │ │ │
│  │  └──────────────────────────────────────────────────────────────────────┘ │ │
│  │                              │                                            │ │
│  │              ┌───────────────┴───────────────┐                            │ │
│  │              │                               │                            │ │
│  │              ▼                               ▼                            │ │
│  │   ┌─────────────────────────┐   ┌─────────────────────────────────────┐  │ │
│  │   │ WARM POOL HAS          │   │ WARM POOL EMPTY                     │  │ │
│  │   │ STOPPED INSTANCES      │   │ (Cold Start Required)               │  │ │
│  │   │                        │   │                                     │  │ │
│  │   │ ASG starts a stopped   │   │ ASG launches NEW instance          │  │ │
│  │   │ instance (30-60s)      │   │ from AMI (2-3 min)                  │  │ │
│  │   └─────────────────────────┘   └─────────────────────────────────────┘  │ │
│  │                              │                                            │ │
│  │                              ▼                                            │ │
│  │   ┌────────────────────────────────────────────────────────────────────┐ │ │
│  │   │ Both paths lead to:                                                │ │ │
│  │   │  • Instance state: "pending" → "running" (30-60s)                 │ │ │
│  │   │  • EC2 Status Checks: 4-5 minutes (BOTTLENECK)                    │ │ │
│  │   │  • Total wait: 5-7 minutes (warm) or 8-12 minutes (cold)          │ │ │
│  │   └────────────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 6: Create Session Record in DynamoDB                                  │ │
│  │                                                                            │ │
│  │  Session Record:                                                           │ │
│  │  {                                                                         │ │
│  │    "session_id": "sess-abc123...",                                        │ │
│  │    "student_id": "42",                                                    │ │
│  │    "student_name": "John Doe",                                            │ │
│  │    "plan": "freemium",                 ← Tier for instance routing        │ │
│  │    "status": "PROVISIONING",           ← Initial status                   │ │
│  │    "instance_id": null or "i-xxx",     ← Set if instance was claimed      │ │
│  │    "instance_ip": null or "10.1.x.x",                                     │ │
│  │    "created_at": 1702834567,                                              │ │
│  │    "expires_at": 1702838167,           ← TTL (1 hour default)             │ │
│  │  }                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 7: Return Response                                                    │ │
│  │                                                                            │ │
│  │  Response:                                                                 │ │
│  │  {                                                                         │ │
│  │    "success": true,                                                        │ │
│  │    "data": {                                                               │ │
│  │      "session_id": "sess-abc123...",                                      │ │
│  │      "status": "provisioning",                                            │ │
│  │      "stage": "instance_starting",                                        │ │
│  │      "progress": 25,                                                       │ │
│  │      "stage_message": "Warming up your AttackBox from the pool..."        │ │
│  │    }                                                                       │ │
│  │  }                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         MOODLE PLUGIN STARTS POLLING                             │
│                         (Every 3 seconds, max 200 attempts = 10 minutes)        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        GET-SESSION-STATUS LAMBDA                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 1: Get Session from DynamoDB                                          │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 2: If No Instance Assigned Yet, Try to Allocate                       │ │
│  │                                                                            │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 2a. Check Instance Pool for AVAILABLE instance (same plan)          │ │ │
│  │  │                                                                      │ │ │
│  │  │ 2b. If not found, check ASG directly for running+healthy instances  │ │ │
│  │  │     that can be claimed                                              │ │ │
│  │  │                                                                      │ │ │
│  │  │ 2c. If found → Claim instance, update session                       │ │ │
│  │  └──────────────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 3: If Instance Assigned, Check Health                                 │ │
│  │                                                                            │ │
│  │  EC2 Status Checks:                                                        │ │
│  │  • System Status: ok/initializing/impaired                                │ │
│  │  • Instance Status: ok/initializing/impaired                              │ │
│  │                                                                            │ │
│  │  Both must be "ok" (2/2 checks passed)                                    │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                         ┌──────────────┴──────────────┐                         │
│                         │                             │                         │
│                         ▼                             ▼                         │
│              ┌─────────────────────┐      ┌─────────────────────────────┐      │
│              │ Health Checks       │      │ Health Checks NOT Passed    │      │
│              │ PASSED (2/2)        │      │ (still initializing)        │      │
│              └──────────┬──────────┘      └──────────────┬──────────────┘      │
│                         │                                │                      │
│                         │                                ▼                      │
│                         │                 ┌─────────────────────────────┐      │
│                         │                 │ Return: status=provisioning │      │
│                         │                 │ stage=waiting_health        │      │
│                         │                 │ progress=85                 │      │
│                         │                 │ (Continue polling...)       │      │
│                         │                 └─────────────────────────────┘      │
│                         │                                                       │
│                         ▼                                                       │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 4: Create Guacamole Connection                                        │ │
│  │                                                                            │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 4a. Authenticate with Guacamole API                                  │ │ │
│  │  │     POST https://guacamole-ip/guacamole/api/tokens                   │ │ │
│  │  │     (admin credentials from environment)                             │ │ │
│  │  └──────────────────────────────────────────────────────────────────────┘ │ │
│  │                              │                                            │ │
│  │                              ▼                                            │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 4b. Create RDP Connection                                            │ │ │
│  │  │     POST /api/session/data/postgresql/connections                    │ │ │
│  │  │     {                                                                │ │ │
│  │  │       "name": "attackbox-{session_id[-8:]}",                        │ │ │
│  │  │       "protocol": "rdp",                                            │ │ │
│  │  │       "parameters": {                                               │ │ │
│  │  │         "hostname": "{instance_private_ip}",                        │ │ │
│  │  │         "port": "3389",                                             │ │ │
│  │  │         "username": "kali",                                         │ │ │
│  │  │         "password": "{rdp_password}",                               │ │ │
│  │  │         "security": "any",                                          │ │ │
│  │  │         "ignore-cert": "true"                                       │ │ │
│  │  │       }                                                             │ │ │
│  │  │     }                                                                │ │ │
│  │  └──────────────────────────────────────────────────────────────────────┘ │ │
│  │                              │                                            │ │
│  │                              ▼                                            │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 4c. Create Session User (optional, for direct URL)                   │ │ │
│  │  │     POST /api/session/data/postgresql/users                          │ │ │
│  │  │     Grant connection permission to user                              │ │ │
│  │  └──────────────────────────────────────────────────────────────────────┘ │ │
│  │                              │                                            │ │
│  │                              ▼                                            │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 4d. Generate Direct URL                                              │ │ │
│  │  │     https://guacamole-ip/guacamole/#/client/{encoded_connection_id} │ │ │
│  │  └──────────────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 5: Update Session to READY                                            │ │
│  │                                                                            │ │
│  │  Session Record Updated:                                                   │ │
│  │  {                                                                         │ │
│  │    "status": "READY",                                                      │ │
│  │    "instance_id": "i-0abc123...",                                         │ │
│  │    "instance_ip": "10.1.10.45",                                           │ │
│  │    "direct_url": "https://guac.../guacamole/#/client/...",               │ │
│  │    "connection_info": {                                                    │ │
│  │      "type": "guacamole",                                                 │ │
│  │      "guacamole_connection_id": "5"                                       │ │
│  │    }                                                                       │ │
│  │  }                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│                                        ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ STEP 6: Return Response                                                    │ │
│  │                                                                            │ │
│  │  {                                                                         │ │
│  │    "success": true,                                                        │ │
│  │    "data": {                                                               │ │
│  │      "session_id": "sess-abc123...",                                      │ │
│  │      "status": "ready",                                                   │ │
│  │      "instance_id": "i-0abc123...",                                       │ │
│  │      "instance_ip": "10.1.10.45",                                         │ │
│  │      "direct_url": "https://guac.../guacamole/#/client/...",             │ │
│  │      "progress": 100,                                                      │ │
│  │      "plan": "freemium"                                                   │ │
│  │    }                                                                       │ │
│  │  }                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    MOODLE PLUGIN RECEIVES "READY" STATUS                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│  1. Stop polling                                                                 │
│  2. Update progress bar to 100%                                                  │
│  3. Show "Launch" button with direct_url                                         │
│  4. Open Guacamole in new tab/iframe                                             │
│  5. Student sees Kali Linux desktop!                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Instance Allocation Decision Tree

```
                    ┌─────────────────────────────────┐
                    │ Need Instance for Plan: X       │
                    │ (freemium/starter/pro)          │
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │ Query Instance Pool (DynamoDB)  │
                    │ WHERE status = "AVAILABLE"      │
                    │ AND plan = X                    │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
          ┌─────────────────┐              ┌─────────────────┐
          │ Found Instance  │              │ Not Found       │
          └────────┬────────┘              └────────┬────────┘
                   │                                │
                   ▼                                ▼
          ┌─────────────────┐              ┌─────────────────────────┐
          │ Verify EC2 is   │              │ Check ASG Directly      │
          │ "running"       │              │ for Running Instances   │
          └────────┬────────┘              └────────────┬────────────┘
                   │                                    │
          ┌────────┴────────┐              ┌────────────┴────────────┐
          │                 │              │                         │
          ▼                 ▼              ▼                         ▼
   ┌────────────┐    ┌────────────┐ ┌────────────────┐      ┌────────────────┐
   │ Running    │    │ Not Running│ │ Found Running  │      │ No Running     │
   │            │    │ (stale)    │ │ + Healthy      │      │ Instances      │
   └─────┬──────┘    └─────┬──────┘ └───────┬────────┘      └───────┬────────┘
         │                 │                │                       │
         ▼                 ▼                ▼                       ▼
   ┌────────────┐    ┌────────────┐ ┌────────────────┐      ┌────────────────┐
   │ Claim with │    │ Skip,      │ │ Check if       │      │ Scale Up ASG   │
   │ Conditional│    │ Try next   │ │ truly available│      │ (warm pool or  │
   │ Update     │    │            │ │ or reclaimable │      │ new instance)  │
   └─────┬──────┘    └────────────┘ └───────┬────────┘      └───────┬────────┘
         │                                  │                       │
         │                   ┌──────────────┴──────────────┐        │
         │                   │                             │        │
         │                   ▼                             ▼        │
         │          ┌────────────────┐           ┌────────────────┐ │
         │          │ Unassigned or  │           │ Assigned to    │ │
         │          │ Dead Session   │           │ Active Session │ │
         │          └───────┬────────┘           └───────┬────────┘ │
         │                  │                            │          │
         │                  ▼                            ▼          │
         │          ┌────────────────┐           ┌────────────────┐ │
         │          │ Claim it!      │           │ Skip, try next │ │
         │          └───────┬────────┘           └────────────────┘ │
         │                  │                                       │
         └──────────────────┼───────────────────────────────────────┘
                            │
                            ▼
                   ┌────────────────┐
                   │ Instance       │
                   │ Allocated!     │
                   │                │
                   │ Update:        │
                   │ - Pool record  │
                   │ - Session      │
                   │ - EC2 tags     │
                   └────────────────┘
```

---

## Timeline: Best Case vs Worst Case

### Best Case: Instance Already Running in Pool (~5-10 seconds)

```
0s   ────────────────────────────────────────────────────────────▶
     │                                                           │
     │ [Click] → [Create Session] → [Find Available] → [Claim]   │
     │           │                   │                  │         │
     │           1s                  2s                 5s        │
     │                                                           │
     │         [Create Guacamole Connection] → [READY!]          │
     │                    │                       │              │
     │                    8s                     10s             │
```

### Normal Case: Instance from Warm Pool (~5-7 minutes)

```
0s                              5min                           7min
────────────────────────────────────────────────────────────────▶
│                                │                              │
│ [Click] → [Scale Up ASG]       │                              │
│           │                    │                              │
│         [Start Stopped         │                              │
│          Instance: 30-60s]     │                              │
│                    │           │                              │
│                  [EC2 Status Checks: 4-5 min]                 │
│                                │                    │         │
│                              [Health OK] → [Guacamole] → [READY!]
```

### Worst Case: Cold Start (~8-12 minutes)

```
0s                                        8min                12min
────────────────────────────────────────────────────────────────▶
│                                           │                   │
│ [Click] → [Scale Up ASG]                  │                   │
│           │                               │                   │
│         [Launch NEW Instance              │                   │
│          from AMI: 2-3 min]               │                   │
│                    │                      │                   │
│                  [Boot: 1-2 min]          │                   │
│                           │               │                   │
│                         [EC2 Status Checks: 4-5 min]          │
│                                           │           │       │
│                                         [Health OK] → [READY!]
```

---

## Background Process: Pool Manager Lambda

The Pool Manager runs every minute to maintain instance pools:

```
┌─────────────────────────────────────────────────────────────────┐
│                    POOL MANAGER (Every 1 minute)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  FOR EACH TIER (freemium, starter, pro):                        │
│                                                                  │
│  1. SYNC INSTANCE POOL                                           │
│     ├── Get instances from ASG                                   │
│     ├── Update DynamoDB pool records                            │
│     ├── Mark terminated instances                               │
│     └── Add new instances with correct "plan" tag               │
│                                                                  │
│  2. CLEANUP EXPIRED SESSIONS                                     │
│     ├── Find sessions past expires_at                           │
│     ├── Terminate associated instances                          │
│     └── Release back to pool                                    │
│                                                                  │
│  3. RELEASE ORPHANED INSTANCES                                   │
│     ├── Find instances with no valid session                    │
│     └── Mark as AVAILABLE                                       │
│                                                                  │
│  4. MANAGE SCALING                                               │
│     ├── Count active sessions for this tier                     │
│     ├── Count available instances for this tier                 │
│     ├── If available < threshold → Scale up                     │
│     └── If excess → Scale down (with cooldown)                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Error Scenarios

```
┌─────────────────────────────────────────────────────────────────┐
│                       ERROR SCENARIOS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. TIMEOUT (>10 minutes polling)                               │
│     └── Frontend shows: "Session creation timed out"            │
│         Cause: ASG at max capacity or AWS issues                │
│                                                                  │
│  2. INSTANCE ALLOCATION TIMEOUT (>8 minutes)                    │
│     └── Lambda marks session as ERROR                           │
│         Message: "Instance allocation timed out"                │
│                                                                  │
│  3. GUACAMOLE CONNECTION FAILED                                 │
│     └── Session READY but no direct_url                         │
│         Frontend shows: "LynkBox ready but no connection URL"   │
│                                                                  │
│  4. INSTANCE TERMINATED UNEXPECTEDLY                            │
│     └── Session marked TERMINATED                               │
│         Student must launch new session                         │
│                                                                  │
│  5. CONCURRENT SESSION LIMIT                                    │
│     └── API returns existing session                            │
│         Message: "You already have an active session"           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary

| Step      | Component                      | Time           |
| --------- | ------------------------------ | -------------- |
| 1         | Click "Launch" → API call      | <1s            |
| 2         | Create session, check existing | <1s            |
| 3         | Find/claim available instance  | 1-5s           |
| 4         | If none: Start from warm pool  | 30-60s         |
| 5         | EC2 Status Checks              | **4-5 min** ⚠️ |
| 6         | Create Guacamole connection    | 1-2s           |
| 7         | Return READY, open desktop     | <1s            |
| **TOTAL** |                                | **5-7 min**    |
