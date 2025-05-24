from sqlalchemy.ext.asyncio import AsyncSession
from misc.internal_classes import TradeExecution, InternalOrder
from uuid import UUID
from dao.dao import OrderDAO, BalanceDAO, TransactionDAO
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

        # 1. Переводим покупателю токены продавца
        # из зарезервированных в blocked_amount единиц
        if not await BalanceDAO.transfer_balance(
            session=session,
            from_user_id=seller_id,
            to_user_id=buyer_id,
            ticker=ticker,
            amount=executed_qty
        ):
            raise ValueError(f"Not enough blocked {ticker}")


        # 2. Переводим продавцу рубли покупателя
        # из зарезервированных в blocked_amount единиц # ERROR from_user.blocked_amount = 0
        if not await BalanceDAO.transfer_balance(
            session=session,
            from_user_id=buyer_id,
            to_user_id=seller_id,
            ticker="RUB",
            amount=executed_price * executed_qty
        ):
            raise ValueError("Not enough blocked RUB")

        # 3. Возвращаем сдачу (если есть)
        if bid_order_change:
            if not await BalanceDAO.unblock_balance(
                session=session,
                user_id=buyer_id,
                ticker="RUB",
                amount=bid_order_change
            ):
                raise ValueError("Not enough blocked RUB")


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
        # await TransactionDAO.add(
        #     session=session,
        #     values=TransactionCreate(
        #         buyer_id=seller_id,
        #         seller_id=buyer_id,
        #         ticker="RUB",
        #         amount=executed_price * executed_qty,
        #         price=1
        #     )
        # )


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