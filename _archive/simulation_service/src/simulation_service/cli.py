"""Interface CLI pour le service de simulation."""

import click
import httpx
import json
from pathlib import Path
from typing import Optional

from .config import get_settings


def get_last_session_file() -> Path:
    """Retourne le chemin du fichier contenant le dernier ID de session."""
    # Utiliser le répertoire du projet au lieu du home pour faciliter l'accès
    # Chercher le répertoire simulation_service
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent  # Remonter jusqu'à simulation_service/
    return project_root / "last_session.txt"


def save_last_session_id(session_id: str) -> None:
    """Sauvegarde le dernier ID de session."""
    try:
        session_file = get_last_session_file()
        session_file.write_text(session_id, encoding="utf-8")
        # Afficher le chemin pour debug (optionnel, peut être retiré en production)
        # click.echo(f"💾 Session sauvegardée dans: {session_file}", err=True)
    except Exception as e:
        # Ignorer les erreurs de sauvegarde silencieusement
        pass


def get_last_session_id() -> Optional[str]:
    """Récupère le dernier ID de session."""
    try:
        session_file = get_last_session_file()
        if session_file.exists():
            return session_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return None


def resolve_session_id(session_id: str) -> str:
    """Résout l'ID de session (gère 'last' ou '-' comme alias)."""
    if session_id in ("last", "-"):
        last_id = get_last_session_id()
        if last_id:
            return last_id
        else:
            raise click.ClickException("Aucune session précédente trouvée. Utilisez un ID de session valide.")
    return session_id


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """LIA Simulation Multi-Agent CLI"""
    pass


def get_client() -> httpx.Client:
    """Crée un client HTTP pour l'API."""
    settings = get_settings()
    base_url = f"http://{settings.host}:{settings.port}"
    
    headers = {}
    if settings.api_token:
        headers["X-LIA-Token"] = settings.api_token
    
    return httpx.Client(base_url=base_url, headers=headers, timeout=30.0)


@cli.command()
@click.option("--agent1", required=True, help="ID du premier agent")
@click.option("--agent2", required=True, help="ID du second agent")
@click.option("--agent-type1", default="lia-primary", help="Type du premier agent")
@click.option("--agent-type2", default="lia-secondary", help="Type du second agent")
@click.option("--max-turns", default=20, type=int, help="Nombre maximum de tours")
@click.option("--scenario", help="Scénario prédéfini")
@click.option("--timeout", default=30, type=int, help="Timeout en secondes")
def start(agent1: str, agent2: str, agent_type1: str, agent_type2: str, max_turns: int, scenario: Optional[str], timeout: int):
    """Démarre une simulation multi-agent."""
    client = get_client()
    
    payload = {
        "agent_configs": [
            {"agent_id": agent1, "agent_type": agent_type1},
            {"agent_id": agent2, "agent_type": agent_type2}
        ],
        "max_turns": max_turns,
        "timeout_seconds": timeout
    }
    
    if scenario:
        payload["scenario"] = scenario
    
    try:
        response = client.post("/simulation/start", json=payload)
        response.raise_for_status()
        
        data = response.json()
        session_id = data['session_id']
        save_last_session_id(session_id)
        
        click.echo(f"✅ Simulation démarrée: {session_id}")
        click.echo(f"   Statut: {data['status']}")
        click.echo(f"   Agents: {', '.join(data['agents'])}")
        click.echo(f"   Début: {data['started_at']}")
        click.echo(f"\n💡 Utilisez 'last' ou '-' pour référencer cette session:")
        click.echo(f"   .\\lia-sim.ps1 message last --agent-id {data['agents'][0]} --content \"Votre message\"")
        click.echo(f"   .\\lia-sim.ps1 status last")
        click.echo(f"\n📝 Fichier de session: {get_last_session_file()}")
        
    except httpx.HTTPStatusError as e:
        click.echo(f"❌ Erreur: {e.response.text}", err=True)
    except Exception as e:
        click.echo(f"❌ Erreur: {e}", err=True)
    finally:
        client.close()


@cli.command()
@click.argument("session_id")
def status(session_id: str):
    """Affiche le statut d'une simulation.
    
    SESSION_ID peut être un ID de session ou 'last' pour la dernière session.
    """
    session_id = resolve_session_id(session_id)
    client = get_client()
    
    try:
        response = client.get(f"/simulation/{session_id}/status")
        response.raise_for_status()
        
        data = response.json()
        click.echo(f"\n📊 Simulation: {data['session_id']}")
        click.echo(f"   Statut: {data['status']}")
        click.echo(f"   Tour: {data['current_turn']}/{data['max_turns']}")
        click.echo(f"   Messages: {data['messages_count']}")
        click.echo(f"   Agents: {', '.join(data['agents'])}")
        
        if data.get("metrics"):
            metrics = data["metrics"]
            click.echo(f"\n📈 Métriques:")
            click.echo(f"   Variabilité: {metrics.get('variability', 0):.2f}")
            click.echo(f"   Autonomie: {metrics.get('autonomy', 0):.2f}")
            click.echo(f"   Curiosité: {metrics.get('curiosity', 0):.2f}")
            click.echo(f"   Cohérence: {metrics.get('coherence', 0):.2f}")
        
    except httpx.HTTPStatusError as e:
        click.echo(f"❌ Erreur: {e.response.text}", err=True)
    except Exception as e:
        click.echo(f"❌ Erreur: {e}", err=True)
    finally:
        client.close()


@cli.command()
@click.argument("session_id")
@click.option("--agent-id", required=True, help="ID de l'agent émetteur")
@click.option("--content", required=True, help="Contenu du message")
def message(session_id: str, agent_id: str, content: str):
    """Envoie un message dans une simulation.
    
    SESSION_ID peut être un ID de session ou 'last' pour la dernière session.
    """
    session_id = resolve_session_id(session_id)
    client = get_client()
    
    payload = {
        "agent_id": agent_id,
        "content": content
    }
    
    try:
        response = client.post(f"/simulation/{session_id}/message", json=payload)
        response.raise_for_status()
        
        data = response.json()
        click.echo(f"✅ Message envoyé")
        click.echo(f"   Réponse de {data['response_agent_id']}: {data['response_content'][:100]}...")
        click.echo(f"   Tour: {data['turn']}")
        click.echo(f"   Gouvernance: {data['governance_verdict']}")
        
    except httpx.HTTPStatusError as e:
        click.echo(f"❌ Erreur: {e.response.text}", err=True)
    except Exception as e:
        click.echo(f"❌ Erreur: {e}", err=True)
    finally:
        client.close()


@cli.command()
@click.argument("session_id")
def stop(session_id: str):
    """Arrête une simulation.
    
    SESSION_ID peut être un ID de session ou 'last' pour la dernière session.
    """
    session_id = resolve_session_id(session_id)
    client = get_client()
    
    try:
        response = client.post(f"/simulation/{session_id}/stop")
        response.raise_for_status()
        
        data = response.json()
        click.echo(f"✅ Simulation arrêtée: {data['session_id']}")
        click.echo(f"   Statut: {data['status']}")
        click.echo(f"   Arrêt: {data['stopped_at']}")
        
        if data.get("final_metrics"):
            metrics = data["final_metrics"]
            click.echo(f"\n📈 Métriques finales:")
            click.echo(f"   Variabilité: {metrics.get('variability', 0):.2f}")
            click.echo(f"   Autonomie: {metrics.get('autonomy', 0):.2f}")
            click.echo(f"   Curiosité: {metrics.get('curiosity', 0):.2f}")
            click.echo(f"   Cohérence: {metrics.get('coherence', 0):.2f}")
        
    except httpx.HTTPStatusError as e:
        click.echo(f"❌ Erreur: {e.response.text}", err=True)
    except Exception as e:
        click.echo(f"❌ Erreur: {e}", err=True)
    finally:
        client.close()


@cli.command()
@click.argument("session_id")
@click.option("--format", "export_format", default="json", type=click.Choice(["json", "csv"]), help="Format d'export")
@click.option("--output", "-o", help="Fichier de sortie (stdout si non spécifié)")
def export(session_id: str, export_format: str, output: Optional[str]):
    """Exporte les résultats d'une simulation.
    
    SESSION_ID peut être un ID de session ou 'last' pour la dernière session.
    """
    session_id = resolve_session_id(session_id)
    client = get_client()
    
    try:
        response = client.get(f"/simulation/{session_id}/export", params={"format": export_format})
        response.raise_for_status()
        
        data = response.json()
        
        if export_format == "json":
            output_data = json.dumps(data, indent=2, default=str)
        else:
            # Format CSV complet avec toutes les métriques
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # En-têtes
            writer.writerow([
                "Session ID", "Started At", "Ended At", "Total Turns",
                "Variability", "Autonomy", "Curiosity", "Coherence",
                "Agents", "Messages Count", "Experience ID"
            ])
            
            # Données principales
            metrics = data.get("metrics", {})
            writer.writerow([
                data['session_id'],
                data['started_at'],
                data.get('ended_at', ''),
                data['total_turns'],
                metrics.get('variability', ''),
                metrics.get('autonomy', ''),
                metrics.get('curiosity', ''),
                metrics.get('coherence', ''),
                ', '.join(data.get('agents', [])),
                len(data.get('messages', [])),
                ', '.join(data.get('experiences_created', []))
            ])
            
            # Métriques par agent
            if data.get('metrics_by_agent'):
                writer.writerow([])
                writer.writerow(["Agent", "Variability", "Autonomy", "Curiosity", "Coherence"])
                for agent_id, agent_metrics in data['metrics_by_agent'].items():
                    writer.writerow([
                        agent_id,
                        agent_metrics.get('variability', ''),
                        agent_metrics.get('autonomy', ''),
                        agent_metrics.get('curiosity', ''),
                        agent_metrics.get('coherence', '')
                    ])
            
            output_data = output.getvalue()
        
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(output_data)
            click.echo(f"✅ Résultats exportés vers {output}")
        else:
            click.echo(output_data)
        
    except httpx.HTTPStatusError as e:
        click.echo(f"❌ Erreur: {e.response.text}", err=True)
    except Exception as e:
        click.echo(f"❌ Erreur: {e}", err=True)
    finally:
        client.close()


if __name__ == "__main__":
    cli()



