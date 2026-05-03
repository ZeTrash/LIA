"""Interface web pour suivre les débats LIA-Gemini en temps réel."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from core import LLMAdapter, CoreConfig
from support import LearningService, SupportConfig
from support.quality_scorer import QualityScorer, calculate_semantic_distance
from memory_service import MemoryAdapter
from test_lia_gemini import lia_debate_with_gemini

app = FastAPI(title="LIA - Interface de Débat")

# Dossier pour les fichiers statiques
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)


class ConnectionManager:
    """Gère les connexions WebSocket."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


def print_flush_websocket(message: str, msg_type: str = "info", websocket: WebSocket = None):
    """Remplace print_flush pour envoyer via WebSocket."""
    if websocket:
        asyncio.create_task(manager.send_message({
            "type": msg_type,
            "content": message,
            "timestamp": asyncio.get_event_loop().time()
        }, websocket))
    else:
        print(message)


@app.get("/")
async def get_index():
    """Page principale."""
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LIA - Interface de Débat</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            h1 { color: #333; }
            .controls { margin: 20px 0; }
            button { padding: 10px 20px; margin: 5px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #45a049; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            #output { margin-top: 20px; padding: 15px; background: #f9f9f9; border-radius: 4px; max-height: 600px; overflow-y: auto; }
            .message { margin: 10px 0; padding: 10px; border-left: 4px solid #ddd; }
            .message.info { border-color: #2196F3; }
            .message.success { border-color: #4CAF50; }
            .message.warning { border-color: #FF9800; }
            .message.error { border-color: #f44336; }
            .message-title { font-weight: bold; margin-bottom: 5px; }
            .timestamp { color: #666; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 LIA - Interface de Débat en Temps Réel</h1>
            <div class="controls">
                <input type="text" id="topic" placeholder="Thématique du débat..." style="width: 400px; padding: 8px;">
                <button onclick="startDebate()" id="startBtn">Démarrer le débat</button>
                <button onclick="clearOutput()" id="clearBtn">Effacer</button>
            </div>
            <div id="output"></div>
        </div>
        <script>
            let ws = null;
            
            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    addMessage(data.content, data.type);
                };
                
                ws.onerror = (error) => {
                    addMessage('Erreur de connexion WebSocket', 'error');
                };
                
                ws.onclose = () => {
                    addMessage('Connexion fermée', 'warning');
                    document.getElementById('startBtn').disabled = false;
                };
            }
            
            function startDebate() {
                const topic = document.getElementById('topic').value;
                if (!topic) {
                    alert('Veuillez entrer une thématique');
                    return;
                }
                
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    connect();
                    setTimeout(() => startDebate(), 500);
                    return;
                }
                
                document.getElementById('startBtn').disabled = true;
                clearOutput();
                ws.send(JSON.stringify({ action: 'start_debate', topic: topic }));
            }
            
            function clearOutput() {
                document.getElementById('output').innerHTML = '';
            }
            
            function addMessage(content, type = 'info') {
                const output = document.getElementById('output');
                const message = document.createElement('div');
                message.className = `message ${type}`;
                message.innerHTML = `
                    <div class="message-title">${getTypeIcon(type)} ${content.substring(0, 100)}${content.length > 100 ? '...' : ''}</div>
                    <div style="margin-top: 5px; white-space: pre-wrap;">${escapeHtml(content)}</div>
                `;
                output.appendChild(message);
                output.scrollTop = output.scrollHeight;
            }
            
            function getTypeIcon(type) {
                const icons = {
                    'info': 'ℹ️',
                    'success': '✅',
                    'warning': '⚠️',
                    'error': '❌',
                    'thesis': '📝',
                    'antithesis': '🔄',
                    'debate': '⚔️',
                    'synthesis': '✨'
                };
                return icons[type] || '•';
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // Connexion automatique au chargement
            window.onload = () => connect();
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket pour le streaming en temps réel."""
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("action") == "start_debate":
                topic = data.get("topic", "L'intelligence artificielle va-t-elle remplacer les humains au travail ?")
                
                # Lancer le débat dans une tâche asyncio
                asyncio.create_task(run_debate_with_websocket(topic, websocket))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def run_debate_with_websocket(topic: str, websocket: WebSocket):
    """Lance un débat et envoie les messages via WebSocket."""
    try:
        # Initialisation
        await manager.send_message({
            "type": "info",
            "content": "🔧 Initialisation de LIA...",
            "timestamp": asyncio.get_event_loop().time()
        }, websocket)
        
        # Configuration
        core_config = CoreConfig(
            model_path="models/Qwen/Qwen2.5-1.5B-Instruct",
            quantize=True,
            quantization_bits=4,
            max_length=512,
            temperature=0.7
        )
        
        support_config = SupportConfig()
        support_config.load_from_file("config/api.conf")
        
        if not support_config.gemini_api_key:
            await manager.send_message({
                "type": "error",
                "content": "❌ Clé API Gemini non configurée",
                "timestamp": asyncio.get_event_loop().time()
            }, websocket)
            return
        
        await manager.send_message({
            "type": "success",
            "content": "✅ Configuration Gemini chargée",
            "timestamp": asyncio.get_event_loop().time()
        }, websocket)
        
        # Initialiser les services
        memory = MemoryAdapter()
        core_adapter = LLMAdapter(core_config, use_memory=True, use_cognitive_planner=True)
        learning_service = LearningService(config=support_config, memory_adapter=memory)
        
        await manager.send_message({
            "type": "success",
            "content": "✅ Services initialisés",
            "timestamp": asyncio.get_event_loop().time()
        }, websocket)
        
        # Lancer le débat avec callback WebSocket
        session_id = "web_debate_session"
        
        await manager.send_message({
            "type": "info",
            "content": f"🎯 LIA travaille sur la thématique: {topic}",
            "timestamp": asyncio.get_event_loop().time()
        }, websocket)
        
        # Modifier la fonction de débat pour utiliser WebSocket
        result = await lia_debate_with_gemini_websocket(
            core_adapter=core_adapter,
            learning_service=learning_service,
            topic=topic,
            session_id=session_id,
            websocket=websocket
        )
        
        await manager.send_message({
            "type": "success",
            "content": "🎉 Débat terminé avec succès !",
            "timestamp": asyncio.get_event_loop().time()
        }, websocket)
        
    except Exception as e:
        await manager.send_message({
            "type": "error",
            "content": f"❌ Erreur: {str(e)}",
            "timestamp": asyncio.get_event_loop().time()
        }, websocket)
        import traceback
        traceback.print_exc()


async def lia_debate_with_gemini_websocket(
    core_adapter: LLMAdapter,
    learning_service: LearningService,
    topic: str,
    session_id: str,
    websocket: WebSocket
) -> Dict[str, Any]:
    """Version WebSocket de lia_debate_with_gemini."""
    result = {
        "topic": topic,
        "thesis": None,
        "antithesis": None,
        "contradiction_score": None,
        "debate": [],
        "convergence_scores": [],
        "synthesis": None,
        "synthesis_validation": None
    }
    
    quality_scorer = QualityScorer()
    
    # Étape 1: Thèse
    await manager.send_message({
        "type": "thesis",
        "content": "📝 Étape 1: LIA développe sa thèse...",
        "timestamp": asyncio.get_event_loop().time()
    }, websocket)
    
    thesis_prompt = f"""Tu es LIA, une intelligence artificielle qui réfléchit profondément. 
Sur le sujet "{topic}", développe une thèse argumentée et cohérente. 
Sois précis, structuré et convaincant. Ta réponse doit être une position claire et défendable."""
    
    thesis = await core_adapter.generate(thesis_prompt, session_id=session_id)
    result["thesis"] = thesis
    
    await manager.send_message({
        "type": "thesis",
        "content": f"🤖 LIA (Thèse):\n{thesis}",
        "timestamp": asyncio.get_event_loop().time()
    }, websocket)
    
    # Étape 2: Questions
    await manager.send_message({
        "type": "info",
        "content": "❓ Étape 2: LIA prépare des questions pour Gemini...",
        "timestamp": asyncio.get_event_loop().time()
    }, websocket)
    
    questions_prompt = f"""Tu es LIA. Tu as développé cette thèse sur "{topic}":
"{thesis}"

Maintenant, tu dois préparer exactement 3 questions critiques à poser à Gemini pour obtenir une perspective opposée (antithèse). 
Ces questions doivent être pertinentes et permettre de challenger ta thèse.

IMPORTANT: Réponds avec UNIQUEMENT les 3 questions, une par ligne, numérotées 1., 2., 3.
Chaque question doit être complète et se terminer par un point d'interrogation.
Ne mets aucun autre texte, juste les 3 questions."""
    
    import re
    questions_text = await core_adapter.generate(questions_prompt, session_id=session_id)
    
    # Extraire questions (simplifié)
    numbered_pattern = re.compile(r'\d+[\.\)]\s*([^\n\d]+)', re.MULTILINE)
    numbered_matches = numbered_pattern.findall(questions_text)
    questions = [q.strip() for q in numbered_matches if q.strip() and ('?' in q or len(q) > 20)][:3]
    
    if not questions:
        questions = [
            f"Quels sont les arguments contre cette position sur {topic} ?",
            f"Quels sont les risques ou limites de cette approche sur {topic} ?",
            f"Quelles sont les perspectives alternatives sur {topic} ?"
        ]
    
    await manager.send_message({
        "type": "info",
        "content": f"🤖 LIA a préparé {len(questions)} questions",
        "timestamp": asyncio.get_event_loop().time()
    }, websocket)
    
    # Étape 3: Antithèse
    await manager.send_message({
        "type": "antithesis",
        "content": "💬 Étape 3: LIA interroge Gemini pour obtenir l'antithèse...",
        "timestamp": asyncio.get_event_loop().time()
    }, websocket)
    
    # Poser les questions à Gemini
    async def ask_gemini(question: str, num: int):
        try:
            answer = await learning_service.gemini.query(question, context=None)
            quality = quality_scorer.score_response(answer, question)
            await manager.send_message({
                "type": "info",
                "content": f"🔍 Question {num}: {question}\n🤖 Gemini: {answer[:200]}...\n📊 Score: {quality['total_score']:.2f}",
                "timestamp": asyncio.get_event_loop().time()
            }, websocket)
            return {"question": question, "answer": answer, "success": True}
        except Exception as e:
            return {"question": question, "answer": None, "success": False, "error": str(e)}
    
    tasks = [ask_gemini(q, i+1) for i, q in enumerate(questions)]
    gemini_responses = await asyncio.gather(*tasks)
    successful_responses = [r for r in gemini_responses if r.get("success", False)]
    
    # Générer antithèse
    if successful_responses:
        antithesis_prompt = f"""Sur le sujet "{topic}", voici la thèse défendue par LIA:
"{thesis}"

Formule une antithèse claire et argumentée qui s'oppose à cette thèse. Sois convaincant et structuré."""
        
        try:
            antithesis = await learning_service.gemini.query(antithesis_prompt, context=None)
            contradiction_distance = calculate_semantic_distance(thesis, antithesis)
            result["antithesis"] = antithesis
            result["contradiction_score"] = contradiction_distance
            
            await manager.send_message({
                "type": "antithesis",
                "content": f"🔄 Antithèse (Gemini):\n{antithesis}\n\n📊 Distance sémantique: {contradiction_distance:.3f}",
                "timestamp": asyncio.get_event_loop().time()
            }, websocket)
        except Exception as e:
            await manager.send_message({
                "type": "error",
                "content": f"⚠️ Erreur génération antithèse: {e}",
                "timestamp": asyncio.get_event_loop().time()
            }, websocket)
    
    # Étape 4: Débat (simplifié à 2 tours pour la démo)
    await manager.send_message({
        "type": "debate",
        "content": "⚔️ Étape 4: Débat entre LIA et Gemini...",
        "timestamp": asyncio.get_event_loop().time()
    }, websocket)
    
    for round_num in range(1, 3):  # 2 tours pour la démo
        await manager.send_message({
            "type": "debate",
            "content": f"--- Tour {round_num} du débat ---",
            "timestamp": asyncio.get_event_loop().time()
        }, websocket)
        
        # LIA défend
        defense_prompt = f"""Tu es LIA. Tu défends ta thèse sur "{topic}":
THÈSE: {thesis}
ANTITHÈSE: {result.get('antithesis', '')}

Défends ta position avec des arguments solides."""
        
        lia_arg = await core_adapter.generate(defense_prompt, session_id=session_id)
        await manager.send_message({
            "type": "debate",
            "content": f"🤖 LIA: {lia_arg[:300]}...",
            "timestamp": asyncio.get_event_loop().time()
        }, websocket)
        
        # Gemini répond
        gemini_prompt = f"""Tu défends l'antithèse sur "{topic}". 
LIA vient de dire: "{lia_arg}"
Réponds en défendant l'antithèse."""
        
        try:
            gemini_arg = await learning_service.gemini.query(gemini_prompt, context=None)
            await manager.send_message({
                "type": "debate",
                "content": f"🤖 Gemini: {gemini_arg[:300]}...",
                "timestamp": asyncio.get_event_loop().time()
            }, websocket)
        except Exception as e:
            await manager.send_message({
                "type": "warning",
                "content": f"⚠️ Gemini n'a pas pu répondre: {e}",
                "timestamp": asyncio.get_event_loop().time()
            }, websocket)
    
    # Étape 5: Synthèse
    await manager.send_message({
        "type": "synthesis",
        "content": "✨ Étape 5: LIA crée une synthèse...",
        "timestamp": asyncio.get_event_loop().time()
    }, websocket)
    
    synthesis_prompt = f"""Tu es LIA. Tu as mené un débat sur "{topic}".
THÈSE: {thesis}
ANTITHÈSE: {result.get('antithesis', '')}

Crée une synthèse qui trouve un terrain d'entente entre la thèse et l'antithèse."""
    
    synthesis = await core_adapter.generate(synthesis_prompt, session_id=session_id)
    result["synthesis"] = synthesis
    
    await manager.send_message({
        "type": "synthesis",
        "content": f"🤖 LIA (Synthèse):\n{synthesis}",
        "timestamp": asyncio.get_event_loop().time()
    }, websocket)
    
    return result


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Interface Web LIA - Débats en Temps Réel")
    print("=" * 70)
    print()
    print("📡 Serveur accessible sur: http://localhost:8000")
    print("🌐 Ou depuis l'extérieur: http://<votre-ip>:8000")
    print()
    print("Appuyez sur Ctrl+C pour arrêter")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8008, log_level="info")

