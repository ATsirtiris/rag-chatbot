# 🎓 MSc Dissertation Project — AI-Powered RAG Chatbot

**Author:** Alexandros Tsirtiris  
**University:** University of York  
**Degree:** MSc Big Data Engineering and Data Science  
**Year:** 2025  

---

## 🧠 Project Overview

This project implements an **AI-powered chatbot** using **Retrieval-Augmented Generation (RAG)** to provide grounded, context-aware responses.  
The system combines **FastAPI**, **OpenAI GPT-4**, **Redis**, and **ChromaDB** for efficient query processing, document retrieval, and conversational memory.

The chatbot allows users to interact naturally while referencing specific documents (such as PDFs) for precise answers.  
Additional features include **dark/light mode**, **session persistence**, and **save/load chat history** for reproducibility.

---

## 🚀 Features

- **Conversational AI:** GPT-4-powered chatbot using OpenAI’s API  
- **Retrieval-Augmented Generation (RAG):**  
  Contextual responses based on document embeddings (OpenAI text-embedding-3-small)  
- **Backend:** FastAPI + Redis memory store  
- **Vector Storage:** ChromaDB for persistent embeddings  
- **Frontend:** Next.js + Tailwind CSS + TypeScript  
- **UI:** Modern interface with dark/light mode and message citations  
- **Session Management:** Save and reload chats (JSON export/import)  
- **Evaluation Pipeline:** Automated script for grounded accuracy, latency, and hallucination rate

---

## 🧩 System Architecture

```mermaid
graph TD
    A[User Interface (Next.js)] -->|REST API Calls| B(FastAPI Backend)
    B --> C[Redis Memory (Session Storage)]
    B --> D[Chroma Vector Store (Document Embeddings)]
    B --> E[OpenAI GPT-4 API]
    D --> F[(PDF / TXT Documents)]
