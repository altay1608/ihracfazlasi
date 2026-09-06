import click
from flask.cli import AppGroup

from app.extensions import db
from app.models import ObligationRecurrencePlan
from app.services.finance import FinanceConfigurationError, sync_recurring_obligations
from app.utils import now_in_istanbul


finance_cli = AppGroup("finance", help="Finans planlama ve dönemsel görevleri.")


@finance_cli.command("sync-recurring-obligations")
@click.option(
    "--through-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Bu tarih dahil vadesi gelen tekrar dönemlerini üretir.",
)
def sync_recurring_obligations_command(through_date):
    """Materialize weekly and monthly obligation periods exactly once."""
    target_date = (
        through_date.date()
        if through_date is not None
        else now_in_istanbul().date()
    )
    try:
        created_count = sync_recurring_obligations(through_date=target_date)
        active_plan_count = ObligationRecurrencePlan.query.filter_by(status="active").count()
        db.session.commit()
    except FinanceConfigurationError as exc:
        db.session.rollback()
        raise click.ClickException(str(exc)) from exc

    click.echo(
        "RECURRING_OBLIGATIONS_SYNC_OK through_date={} created={} active_plans={}".format(
            target_date.isoformat(),
            created_count,
            active_plan_count,
        )
    )


def register_finance_cli(app):
    app.cli.add_command(finance_cli)
