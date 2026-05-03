"""Dashboard terminal pour visualiser les simulations en temps réel."""

import time
import httpx
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn

from .config import get_settings


def display_dashboard(session_id: str, refresh_interval: float = 2.0):
    """Affiche un dashboard en temps réel pour une simulation."""
    console = Console()
    settings = get_settings()
    base_url = f"http://{settings.host}:{settings.port}"
    
    headers = {}
    if settings.api_token:
        headers["X-LIA-Token"] = settings.api_token
    
    client = httpx.Client(base_url=base_url, headers=headers, timeout=30.0)
    
    try:
        with Live(console=console, refresh_per_second=1/refresh_interval) as live:
            while True:
                try:
                    response = client.get(f"/simulation/{session_id}/status")
                    response.raise_for_status()
                    data = response.json()
                    
                    # Créer le tableau principal
                    table = Table(title=f"Simulation: {data['session_id']}", show_header=True)
                    table.add_column("Propriété", style="cyan")
                    table.add_column("Valeur", style="green")
                    
                    table.add_row("Statut", data['status'])
                    table.add_row("Tour", f"{data['current_turn']}/{data['max_turns']}")
                    table.add_row("Messages", str(data['messages_count']))
                    table.add_row("Agents", ", ".join(data['agents']))
                    table.add_row("Début", str(data['started_at']))
                    
                    if data.get("last_activity"):
                        table.add_row("Dernière activité", str(data['last_activity']))
                    
                    # Métriques
                    if data.get("metrics"):
                        metrics = data["metrics"]
                        metrics_table = Table(title="Métriques comportementales", show_header=True)
                        metrics_table.add_column("Métrique", style="cyan")
                        metrics_table.add_column("Valeur", style="green")
                        metrics_table.add_column("Barre", style="yellow")
                        
                        for metric_name in ["variability", "autonomy", "curiosity", "coherence"]:
                            value = metrics.get(metric_name, 0.0)
                            bar = "█" * int(value * 10) + "░" * (10 - int(value * 10))
                            metrics_table.add_row(
                                metric_name.capitalize(),
                                f"{value:.2f}",
                                bar
                            )
                        
                        # Créer le panel avec les deux tableaux
                        panel_content = f"{table}\n\n{metrics_table}"
                        panel = Panel(panel_content, title="Dashboard Simulation", border_style="blue")
                        live.update(panel)
                    else:
                        panel = Panel(str(table), title="Dashboard Simulation", border_style="blue")
                        live.update(panel)
                    
                    # Vérifier si la simulation est terminée
                    if data['status'] in ['stopped', 'failed', 'completed']:
                        console.print(f"\n[bold red]Simulation terminée: {data['status']}[/bold red]")
                        break
                    
                    time.sleep(refresh_interval)
                    
                except KeyboardInterrupt:
                    console.print("\n[bold yellow]Arrêt du dashboard...[/bold yellow]")
                    break
                except Exception as e:
                    console.print(f"[bold red]Erreur: {e}[/bold red]")
                    time.sleep(refresh_interval)
    
    finally:
        client.close()


def display_messages(session_id: str, limit: int = 10):
    """Affiche les derniers messages d'une simulation."""
    console = Console()
    settings = get_settings()
    base_url = f"http://{settings.host}:{settings.port}"
    
    headers = {}
    if settings.api_token:
        headers["X-LIA-Token"] = settings.api_token
    
    client = httpx.Client(base_url=base_url, headers=headers, timeout=30.0)
    
    try:
        response = client.get(f"/simulation/{session_id}/export")
        response.raise_for_status()
        data = response.json()
        
        messages = data.get("messages", [])
        if not messages:
            console.print("[yellow]Aucun message trouvé[/yellow]")
            return
        
        # Afficher les derniers messages
        table = Table(title=f"Derniers messages ({min(limit, len(messages))})", show_header=True)
        table.add_column("Tour", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Contenu", style="white", max_width=60)
        table.add_column("Timestamp", style="dim")
        
        for msg in messages[-limit:]:
            turn = msg.get("metadata", {}).get("turn", "?")
            agent_id = msg.get("agent_id", "?")
            content = msg.get("content", "")[:60] + "..." if len(msg.get("content", "")) > 60 else msg.get("content", "")
            timestamp = msg.get("timestamp", "?")
            
            table.add_row(str(turn), agent_id, content, str(timestamp))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]Erreur: {e}[/bold red]")
    finally:
        client.close()



