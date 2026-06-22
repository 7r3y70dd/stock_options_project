"""Initial database schema migration.

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('risk_level', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('paper_trading_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('live_trading_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('live_trading_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('initial_portfolio_value', sa.Float(), nullable=False, server_default='100000.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create watchlists table
    op.create_table(
        'watchlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_watchlists_user_id'), 'watchlists', ['user_id'])

    # Create watchlist_symbols table
    op.create_table(
        'watchlist_symbols',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('watchlist_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['watchlist_id'], ['watchlists.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_watchlist_symbols_watchlist_id'), 'watchlist_symbols', ['watchlist_id'])
    op.create_index(op.f('ix_watchlist_symbols_symbol'), 'watchlist_symbols', ['symbol'])

    # Create option_contracts table
    op.create_table(
        'option_contracts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('expiration', sa.String(10), nullable=False),
        sa.Column('strike', sa.Float(), nullable=False),
        sa.Column('contract_type', sa.String(10), nullable=False),
        sa.Column('bid', sa.Float(), nullable=False),
        sa.Column('ask', sa.Float(), nullable=False),
        sa.Column('volume', sa.Integer(), nullable=False),
        sa.Column('open_interest', sa.Integer(), nullable=False),
        sa.Column('implied_volatility', sa.Float(), nullable=False),
        sa.Column('underlying_price', sa.Float(), nullable=False),
        sa.Column('days_to_expiration', sa.Integer(), nullable=False),
        sa.Column('earnings_date', sa.String(10), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_option_contracts_symbol'), 'option_contracts', ['symbol'])
    op.create_index(op.f('ix_option_contracts_expiration'), 'option_contracts', ['expiration'])

    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('option_contract_id', sa.Integer(), nullable=False),
        sa.Column('signal_type', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['option_contract_id'], ['option_contracts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_signals_user_id'), 'signals', ['user_id'])
    op.create_index(op.f('ix_signals_option_contract_id'), 'signals', ['option_contract_id'])

    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('option_contract_id', sa.Integer(), nullable=False),
        sa.Column('trade_type', sa.String(10), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='open'),
        sa.Column('is_paper_trading', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_pct', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['option_contract_id'], ['option_contracts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trades_user_id'), 'trades', ['user_id'])
    op.create_index(op.f('ix_trades_option_contract_id'), 'trades', ['option_contract_id'])

    # Create backtest_results table
    op.create_table(
        'backtest_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('strategy_name', sa.String(255), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('start_date', sa.String(10), nullable=False),
        sa.Column('end_date', sa.String(10), nullable=False),
        sa.Column('initial_capital', sa.Float(), nullable=False),
        sa.Column('final_capital', sa.Float(), nullable=False),
        sa.Column('total_return_pct', sa.Float(), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('losing_trades', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=False),
        sa.Column('max_drawdown_pct', sa.Float(), nullable=False),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('parameters', sa.Text(), nullable=True),
        sa.Column('results_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_backtest_results_user_id'), 'backtest_results', ['user_id'])
    op.create_index(op.f('ix_backtest_results_symbol'), 'backtest_results', ['symbol'])


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index(op.f('ix_backtest_results_symbol'), table_name='backtest_results')
    op.drop_index(op.f('ix_backtest_results_user_id'), table_name='backtest_results')
    op.drop_table('backtest_results')
    op.drop_index(op.f('ix_trades_option_contract_id'), table_name='trades')
    op.drop_index(op.f('ix_trades_user_id'), table_name='trades')
    op.drop_table('trades')
    op.drop_index(op.f('ix_signals_option_contract_id'), table_name='signals')
    op.drop_index(op.f('ix_signals_user_id'), table_name='signals')
    op.drop_table('signals')
    op.drop_index(op.f('ix_option_contracts_expiration'), table_name='option_contracts')
    op.drop_index(op.f('ix_option_contracts_symbol'), table_name='option_contracts')
    op.drop_table('option_contracts')
    op.drop_index(op.f('ix_watchlist_symbols_symbol'), table_name='watchlist_symbols')
    op.drop_index(op.f('ix_watchlist_symbols_watchlist_id'), table_name='watchlist_symbols')
    op.drop_table('watchlist_symbols')
    op.drop_index(op.f('ix_watchlists_user_id'), table_name='watchlists')
    op.drop_table('watchlists')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
