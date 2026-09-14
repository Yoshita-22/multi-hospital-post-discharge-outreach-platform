from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.outbound_call import OutboundCall
from app.schemas.conversation import ConversationResult

class OutboundCallService:
    @staticmethod
    async def save_conversation_result(db: AsyncSession, result: ConversationResult) -> OutboundCall:
        """
        Saves the ConversationResult into the OutboundCall table.
        """
        outbound_call = OutboundCall(
            id=result.call_id,
            campaign_id=result.campaign_id,
            patient_id=result.patient_id,
            outcome=result.outcome.value,
            patient_reached=result.patient_reached,
            responses=result.responses,
            symptoms_reported=result.symptoms_reported,
            uncertainties=result.uncertainties,
            callback_requested=result.callback_requested,
            callback_time=result.callback_time,
            transcript=result.transcript,
            summary=result.summary,
            started_at=result.started_at,
            completed_at=result.completed_at
        )
        
        db.add(outbound_call)
        await db.commit()
        await db.refresh(outbound_call)
        
        return outbound_call
