# SwiftChat

A real-time chat platform built with Django, Django REST Framework, PostgreSQL, Redis, and WebSockets.

SwiftChat supports direct messaging, group conversations, file sharing, reactions, replies, notifications, read receipts, and real-time communication using Django Channels.

---

# Features

## Authentication

- User Registration
- User Login
- JWT Authentication
- Secure Protected APIs

---

## Conversations

- Direct Conversations
- Group Conversations
- Add Members
- Remove Members
- Leave Group
- Transfer Ownership
- Rename Group
- Delete Group

---

## Messaging

- Send Messages
- Edit Messages
- Delete Messages
- Message Pagination
- Message Search
- Reply To Messages
- Forward Messages
- Pin Messages

---

## Realtime Features

Powered by Django Channels and Redis.

- Real-time Messaging
- Typing Indicators
- User Presence (Online/Offline)
- Delivery Receipts
- Read Receipts
- Real-time Notifications

---

## Reactions

- Add Reactions
- Remove Reactions
- Real-time Reaction Updates

---

## Mentions

Users can mention other users inside conversations.

Example:

@john Please review the API changes.

Mentioned users receive notifications.

---

## Notifications

- Reactions
- Mentions
- Group Invites

Notifications are delivered in real-time through WebSockets.

---

## File Attachments

Supported file types:

- JPG
- JPEG
- PNG
- PDF
- DOCX

Unsupported file types are rejected.

Examples:

- Images
- Documents
- PDFs

---

## Search

Search messages by:

- Message Content
- Sender Email

Supports pagination.

---

## Docker Support

The application can be started using Docker Compose.

Includes:

- Django
- PostgreSQL
- Redis

---

# Tech Stack

## Backend

- Python
- Django
- Django REST Framework
- Django Channels

## Database

- PostgreSQL

## Realtime

- Redis
- WebSockets

## Authentication

- JWT
- SimpleJWT

## Documentation

- Swagger/OpenAPI
- drf-spectacular

## DevOps

- Docker
- Docker Compose
- GitHub Actions

---

# Architecture

```text
Client
│
├── REST API
│
▼
Django REST Framework
│
▼
PostgreSQL


Client
│
├── WebSocket
│
▼
Django Channels
│
▼
Redis Channel Layer
│
▼
Connected Users
```

---

# Database Design

## Conversation

```text
Conversation
├── id
├── name
├── is_group
├── created_by
├── created_at
└── updated_at
```

## ConversationMember

```text
ConversationMember
├── conversation
├── user
└── joined_at
```

## Message

```text
Message
├── conversation
├── sender
├── content
├── attachment
├── reply_to
├── forwarded_from
├── is_pinned
├── is_edited
└── created_at
```

## MessageReceipt

```text
MessageReceipt
├── message
├── user
├── delivered
├── seen
├── delivered_at
└── seen_at
```

## MessageReaction

```text
MessageReaction
├── message
├── user
└── emoji
```

## Notification

```text
Notification
├── recipient
├── actor
├── notification_type
├── message
├── is_read
└── created_at
```

---

# API Documentation

Swagger UI:

http://localhost:8000/api/swagger/

ReDoc:

http://localhost:8000/api/redoc/

---

# Installation

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/swiftchat.git
cd swiftchat
```

## Create Virtual Environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a .env file:

```env
SECRET_KEY=your_secret_key

DB_NAME=swiftchat
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

---

## Run Migrations

```bash
python manage.py migrate
```

---

## Start Redis

```bash
redis-server
```

---

## Run Server

```bash
python manage.py runserver
```

---

# Docker Setup

Start everything:

```bash
docker compose up --build
```

Stop:

```bash
docker compose down
```

---

# Running Tests

```bash
python manage.py test
```

---

# Continuous Integration

GitHub Actions automatically:

- Installs dependencies
- Runs migrations
- Executes tests

on every push and pull request.

---

# Project Highlights

- JWT Authentication
- PostgreSQL Database Design
- Redis-based Realtime Communication
- WebSocket Architecture
- File Upload System
- Notification System
- Dockerized Environment
- Automated Testing
- CI/CD with GitHub Actions

---

# Future Improvements

Version 2:

- AI-powered Semantic Search
- AI Conversation Summaries
- Vector Embeddings
- pgvector Integration
- RAG-based Message Retrieval

---

# Author

Dina

Built as a portfolio project to demonstrate backend engineering, database design, real-time systems, WebSockets, Redis, PostgreSQL, Docker, and modern API development practices.