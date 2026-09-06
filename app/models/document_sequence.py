from sqlalchemy import UniqueConstraint, event, text

from app.extensions import db


class SiteDocumentSequence(db.Model):
    __tablename__ = "site_document_sequences"
    __table_args__ = (
        UniqueConstraint("site_id", "document_type", name="uq_site_document_sequences_site_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(
        db.Integer,
        db.ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type = db.Column(db.String(40), nullable=False)
    last_value = db.Column(db.Integer, nullable=False, default=0)


def _next_document_number(connection, site_id, document_type):
    if not site_id:
        raise ValueError("Belge numarası için site bilgisi zorunludur.")

    params = {"site_id": int(site_id), "document_type": str(document_type)}
    if connection.dialect.name == "postgresql":
        return int(
            connection.execute(
                text(
                    """
                    INSERT INTO site_document_sequences (site_id, document_type, last_value)
                    VALUES (:site_id, :document_type, 1)
                    ON CONFLICT (site_id, document_type)
                    DO UPDATE SET last_value = site_document_sequences.last_value + 1
                    RETURNING last_value
                    """
                ),
                params,
            ).scalar_one()
        )

    current = connection.execute(
        text(
            """
            SELECT last_value
            FROM site_document_sequences
            WHERE site_id = :site_id AND document_type = :document_type
            """
        ),
        params,
    ).scalar_one_or_none()
    if current is None:
        connection.execute(
            text(
                """
                INSERT INTO site_document_sequences (site_id, document_type, last_value)
                VALUES (:site_id, :document_type, 1)
                """
            ),
            params,
        )
        return 1

    next_value = int(current) + 1
    connection.execute(
        text(
            """
            UPDATE site_document_sequences
            SET last_value = :last_value
            WHERE site_id = :site_id AND document_type = :document_type
            """
        ),
        {**params, "last_value": next_value},
    )
    return next_value


def register_document_number(model, document_type):
    @event.listens_for(model, "before_insert")
    def assign_document_number(_mapper, connection, target):
        if target.document_no is None:
            target.document_no = _next_document_number(connection, target.site_id, document_type)

