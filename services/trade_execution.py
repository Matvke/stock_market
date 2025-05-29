from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from misc.db_models import Balance
from misc.internal_classes import TradeExecution, InternalOrder
from uuid import UUID
from dao.dao import OrderDAO, TransactionDAO
from schemas.create import TransactionCreate
import logging


class TradeExecutor:
    def __init__(self):
        pass

    
    async def execute_trade(self, session: AsyncSession, executions: list[TradeExecution]):
        if not session.in_transaction():
            async with session.begin():
                await self._execute_trade(session, executions)
        else:
            await self._execute_trade(session, executions)


    async def _execute_trade(self, session: AsyncSession, executions: list[TradeExecution]):
        for execution in executions:
            await self._process_execution(
                session=session,
                buyer_id = execution.bid_order.user_id,
                seller_id=execution.ask_order.user_id,
                ticker=execution.bid_order.ticker,
                executed_price=execution.execution_price,
                executed_qty=execution.executed_qty,
                bid_order_change=execution.bid_order_change)
            
            await self._update_orders(
                session=session,
                bid_order=execution.bid_order,
                ask_order=execution.ask_order)
            logging.info(f"Executed: bid:{execution.bid_order.id}, ask:{execution.ask_order.id}")
            
            

    async def _process_execution(
            self,
            session: AsyncSession, 
            buyer_id: UUID, 
            seller_id: UUID, 
            ticker: str, 
            executed_price: int, 
            executed_qty: int,
            bid_order_change: int):
        await self._transfer_of_funds(session, buyer_id, seller_id, ticker, executed_price, executed_qty, bid_order_change)
        await self._save_trade(session, buyer_id, seller_id, ticker, executed_price, executed_qty)


    async def _transfer_of_funds(
            self,
            session: AsyncSession, 
            buyer_id: UUID, 
            seller_id: UUID, 
            ticker: str, 
            executed_price: int, 
            executed_qty: int,
            bid_order_change: int):

        # 1. Лочим seller токены
        seller_balance = (await session.execute(
            select(Balance)
            .where(
                Balance.user_id == seller_id,
                Balance.ticker == ticker)
            .with_for_update()
        )).scalar_one_or_none()
        if not seller_balance or seller_balance.blocked_amount < executed_qty:
            raise ValueError(f"Not enough blocked {ticker}")
        
        # 2. Лочим buyer рубли
        buyer_rub_balance = (await session.execute(
            select(Balance)
            .where(Balance.user_id == buyer_id, Balance.ticker == "RUB")
            .with_for_update()
        )).scalar_one_or_none()
        if not buyer_rub_balance or buyer_rub_balance.blocked_amount < executed_price * executed_qty:
            raise ValueError("Not enough blocked RUB")
        
        # 3. Лочим buyer рубли
        buyer_token_balance = (await session.execute(
            select(Balance)
            .where(Balance.user_id == buyer_id, Balance.ticker == ticker)
            .with_for_update()
        )).scalar_one_or_none()

        # 4. Лочим seller рубли
        seller_rub_balance = (await session.execute(
            select(Balance)
            .where(Balance.user_id == seller_id, Balance.ticker == "RUB")
            .with_for_update()
        )).scalar_one_or_none()

        # 5. Списание токенов у seller 
        seller_balance.blocked_amount -= executed_qty

        # 6. Зачисление токенов buyer 
        if buyer_token_balance:
            buyer_token_balance.amount += executed_qty
        else:
            session.add(Balance(
                user_id=buyer_id,
                ticker=ticker,
                amount=executed_qty,
                blocked_amount=0
            ))

        # 7. Списание рубля у buyer
        buyer_rub_balance.blocked_amount -= executed_price * executed_qty

        # 8. Зачисление рубля seller
        seller_rub_balance.amount += executed_price * executed_qty

        if bid_order_change:
            if buyer_rub_balance.blocked_amount < bid_order_change:
                raise ValueError("Not enough blocked RUB for change")
            buyer_rub_balance.blocked_amount -= bid_order_change
            buyer_rub_balance.amount += bid_order_change

        await session.flush()



    async def _save_trade(
            self,
            session: AsyncSession, 
            buyer_id: UUID, seller_id: 
            UUID, ticker: str, 
            executed_price: int, 
            executed_qty: int):
        
        # 4. Фиксируем транзакцию перевода токенов
        await TransactionDAO.add(
            session=session,
            values=TransactionCreate(
                buyer_id=buyer_id,
                seller_id=seller_id,
                ticker=ticker,
                amount=executed_qty,
                price=executed_price
            )
        )


    async def _update_orders(
            self,
            session: AsyncSession,
            bid_order: InternalOrder,
            ask_order: InternalOrder):
        
    # 6. Обновляем статусы ордеров
        await OrderDAO.update_after_trade(
            session,
            bid_order.id,
            bid_order.filled,
            bid_order.status
        )

        await OrderDAO.update_after_trade(
            session,
            ask_order.id,
            ask_order.filled,
            ask_order.status
        )


trade_executor = TradeExecutor()