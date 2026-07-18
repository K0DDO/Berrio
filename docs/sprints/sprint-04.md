# Sprint 4 — Categorization

## Goal

Hierarchical categories + rule engine + AI stub; auto-tag receipt items; user override → personal rule.

## Pipeline

1. User rules  
2. System rules  
3. AI keyword stub (Kimi later)  
4. Fallback `other`  
5. User override → new `category_rules` row  

## API

- `GET /categories`
- `POST /categories/preview`
- `POST /receipt-items/{id}/category`

## Migration

`0004_categories`
