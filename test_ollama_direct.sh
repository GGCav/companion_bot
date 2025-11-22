#!/bin/bash

echo "=== Testing Ollama Directly ==="
echo ""

echo "1. Testing simple prompt:"
ollama run llama3.2:1b "Say hello in one sentence"
echo ""

echo "2. Testing with emotion tag:"
ollama run llama3.2:1b "You are Buddy. Respond with [happy] tag at start. Say hello."
echo ""

echo "3. Testing with short system prompt:"
ollama run llama3.2:1b "You are Buddy, a pet robot. Format: [emotion] message. Say hello."
echo ""

echo "=== Check Ollama Status ==="
ollama ps
echo ""

echo "=== Check Ollama Logs (last 20 lines) ==="
echo "Run: journalctl -u ollama -n 20"
echo "Or check: ~/.ollama/logs/"
