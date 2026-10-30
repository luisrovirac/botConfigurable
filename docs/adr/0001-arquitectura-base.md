# ADR 0001: Arquitectura base

Fecha: 2026-10-27

## Estado
Aceptado

## Contexto
Seguir plan maestro: multiinquilino con tenant_id + RLS, FSM, outbox con SendPolicy, cola Postgres, etc.

## Decisión
Implementar estructura modular con puertos/adaptadores, configuración con pydantic-settings, logging estructurado.

## Consecuencias
Base sólida para fases siguientes.
