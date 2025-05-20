from sqlalchemy.ext.asyncio import AsyncSession
from misc.internal_classes import TradeExecution
from misc.enums import StatusEnum
from uuid import UUID
from dao.dao import OrderDAO, BalanceDAO, TransactionDAO
from schemas.create import TransactionCreate


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
                bid_order_id=execution.bid_order.id,
                ask_order_id=execution.ask_order.id,
                filled_delta=execution.executed_qty,
                bid_new_status=execution.bid_order.status,
                ask_new_status=execution.ask_order.status)


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
        

        # 1. Производим транзакцию перевода токенов 
        # (из зарезервированных в ask ордере единиц)
        await BalanceDAO.upsert_balance(
            session=session,
            user_id=buyer_id,
            ticker=ticker,
            amount=executed_qty)
        
        # 2. Производим транзакцию перевода рублей
        # (из зарезервированных в bid ордере единиц)
        await BalanceDAO.upsert_balance(
            session=session,
            user_id=seller_id,
            ticker="RUB",
            amount=executed_price * executed_qty
        )

        # 3. Возвращаем сдачу (если есть)
        if bid_order_change:
            await BalanceDAO.upsert_balance(
                session=session,
                user_id=buyer_id,
                ticker="RUB",
                amount=bid_order_change
            )


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

        # 5. Фиксируем транзакцию перевода рублей
        await TransactionDAO.add(
            session=session,
            values=TransactionCreate(
                buyer_id=seller_id,
                seller_id=buyer_id,
                ticker="RUB",
                amount=executed_price * executed_qty,
                price=1
            )
        )


    async def _update_orders(
            self,
            session: AsyncSession,
            bid_order_id: UUID,
            filled_delta: int,
            bid_new_status: StatusEnum,
            ask_order_id: UUID,
            ask_new_status: StatusEnum):
        
    # 6. Обновляем статусы ордеров
        await OrderDAO.update_after_trade(
            session,
            bid_order_id,
            filled_delta,
            bid_new_status
        )

        await OrderDAO.update_after_trade(
            session,
            ask_order_id,
            filled_delta,
            ask_new_status
        )


trade_executor = TradeExecutor()