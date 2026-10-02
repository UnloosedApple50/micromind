"""CLI — command-line interface for MicroMind."""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from micromind.core.runtime import CoreRuntime
from micromind.storage.backends import FlatFileBackend, SQLiteBackend

app = typer.Typer(
    name="micromind",
    help="Agente empresarial ultraleve com capacidades de IA desacopladas",
    no_args_is_help=True,
)
console = Console()


@app.command()
def setup():
    """Run setup wizard."""
    console.print(Panel.fit("[bold green]MicroMind — Setup[/bold green]"))
    console.print("Detecting system...")
    runtime = CoreRuntime()
    console.print(f"Profile: [green]{runtime.profile.value}[/green]")
    console.print(f"OS: {runtime.system_info.os}")
    console.print(f"CPU: {runtime.system_info.cpu}")
    console.print("\n[bold]Setup complete![/bold]")


@app.command()
def doctor():
    """Run system diagnostics."""
    console.print(Panel.fit("[bold blue]MicroMind — Diagnostics[/bold blue]"))
    runtime = CoreRuntime()
    info = runtime.doctor()

    table = Table(title="System Information")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    for key, value in info.items():
        table.add_row(key.upper(), str(value))

    console.print(table)


@app.command()
def status():
    """Show system status."""
    console.print(Panel.fit("[bold green]MicroMind — Status[/bold green]"))
    runtime = CoreRuntime()
    status = runtime.status()

    table = Table(title="System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    for key, value in status.items():
        table.add_row(key.upper(), str(value))

    console.print(table)


@app.command()
def contact_add(
    name: str = typer.Argument(..., help="Contact name"),
    email: str = typer.Option("", "--email", "-e", help="Email address"),
    phone: str = typer.Option("", "--phone", "-p", help="Phone number"),
    company: str = typer.Option("", "--company", "-c", help="Company name"),
):
    """Add a new contact."""
    storage = FlatFileBackend()
    contact_id = f"contact_{name.lower().replace(' ', '_')}"
    storage.set(contact_id, {
        "name": name,
        "email": email,
        "phone": phone,
        "company": company,
    })
    console.print(f"[green]✅ Contact '{name}' added successfully![/green]")


@app.command()
def contact_search(
    query: str = typer.Argument(..., help="Search query"),
):
    """Search contacts."""
    storage = FlatFileBackend()
    results = storage.search(query)

    if not results:
        console.print("[yellow]No contacts found.[/yellow]")
        return

    table = Table(title=f"Search Results: '{query}'")
    table.add_column("Key", style="cyan")
    table.add_column("Field", style="magenta")
    table.add_column("Value", style="green")

    for result in results:
        table.add_row(result["key"], result["field"], result["value"])

    console.print(table)


@app.command()
def task_add(
    title: str = typer.Argument(..., help="Task title"),
    description: str = typer.Option("", "--description", "-d", help="Task description"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority (low, medium, high, urgent)"),
):
    """Add a new task."""
    storage = FlatFileBackend()
    task_id = f"task_{title.lower().replace(' ', '_')}"
    storage.set(task_id, {
        "title": title,
        "description": description,
        "priority": priority,
        "status": "pending",
    })
    console.print(f"[green]✅ Task '{title}' added successfully![/green]")


@app.command()
def task_list():
    """List all tasks."""
    storage = FlatFileBackend()
    keys = storage.list_keys()
    tasks = [k for k in keys if k.startswith("task_")]

    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

    table = Table(title="Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Priority", style="magenta")
    table.add_column("Status", style="yellow")

    for task_key in tasks:
        task = storage.get(task_key)
        if task:
            table.add_row(
                task_key,
                task.get("title", ""),
                task.get("priority", ""),
                task.get("status", ""),
            )

    console.print(table)


@app.command()
def task_complete(
    task_id: str = typer.Argument(..., help="Task ID to complete"),
):
    """Mark a task as completed."""
    storage = FlatFileBackend()
    task = storage.get(task_id)
    if not task:
        console.print(f"[red]❌ Task '{task_id}' not found.[/red]")
        return

    task["status"] = "completed"
    storage.set(task_id, task)
    console.print(f"[green]✅ Task '{task_id}' completed![/green]")


@app.command()
def ticket_create(
    title: str = typer.Argument(..., help="Ticket title"),
    customer: str = typer.Option("", "--customer", "-c", help="Customer name"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority"),
):
    """Create a new ticket."""
    storage = FlatFileBackend()
    ticket_id = f"ticket_{title.lower().replace(' ', '_')}"
    storage.set(ticket_id, {
        "title": title,
        "customer": customer,
        "priority": priority,
        "status": "new",
    })
    console.print(f"[green]✅ Ticket '{title}' created successfully![/green]")


@app.command()
def ticket_list():
    """List all tickets."""
    storage = FlatFileBackend()
    keys = storage.list_keys()
    tickets = [k for k in keys if k.startswith("ticket_")]

    if not tickets:
        console.print("[yellow]No tickets found.[/yellow]")
        return

    table = Table(title="Tickets")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Customer", style="magenta")
    table.add_column("Status", style="yellow")

    for ticket_key in tickets:
        ticket = storage.get(ticket_key)
        if ticket:
            table.add_row(
                ticket_key,
                ticket.get("title", ""),
                ticket.get("customer", ""),
                ticket.get("status", ""),
            )

    console.print(table)


@app.command()
def offer_create(
    customer_id: str = typer.Argument(..., help="Customer ID"),
    object: str = typer.Option(..., "--object", "-o", help="Object of the offer"),
    amount: float = typer.Option(..., "--amount", "-a", help="Offer amount"),
    currency: str = typer.Option("EUR", "--currency", "-c", help="Currency"),
):
    """Create a new offer."""
    storage = FlatFileBackend()
    offer_id = f"offer_{uuid.uuid4().hex[:8]}"
    storage.set(offer_id, {
        "customer_id": customer_id,
        "object": object,
        "amount": amount,
        "currency": currency,
        "status": "new",
    })
    console.print(f"[green]✅ Offer created successfully! ID: {offer_id}[/green]")


@app.command()
def automation_list():
    """List all automation rules."""
    console.print("[yellow]Automation rules not yet implemented.[/yellow]")


@app.command()
def ai_status():
    """Show AI status."""
    console.print(Panel.fit("[bold blue]MicroMind — AI Status[/bold blue]"))
    console.print("Provider: [green]MicroAI[/green]")
    console.print("LLM: [yellow]Not configured[/yellow]")
    console.print("Gateway: [yellow]Not configured[/yellow]")


@app.command()
def call_status():
    """Show telephony status."""
    console.print(Panel.fit("[bold blue]MicroMind — Telephony Status[/bold blue]"))
    console.print("Provider: [yellow]Not configured[/yellow]")
    console.print("Gateway: [yellow]Not configured[/yellow]")
    console.print("Policy: [green]Disabled[/green]")


@app.command()
def call_history():
    """Show call history."""
    console.print("[yellow]No calls yet.[/yellow]")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
