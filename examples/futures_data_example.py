"""
Example usage of the futures data handler for trading systems.

This script demonstrates:
- Creating futures contracts
- Fetching and validating data
- Cleaning and preprocessing
- Building continuous contracts
- Storing data efficiently
- Handling timezones
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

# Import from the SDK
from claude_sdk.data_handler import (
    FuturesContract,
    FuturesDataHandler,
    DataType,
    TimeFrame,
    MarketData,
    DataSource,
    TimeZoneHandler
)


# Example data source implementation
class MockDataSource(DataSource):
    """Mock data source for demonstration."""
    
    async def fetch_historical(
        self,
        contract: FuturesContract,
        data_type: DataType,
        start: datetime,
        end: datetime,
        timeframe: TimeFrame = None
    ) -> MarketData:
        """Generate mock historical data."""
        # Generate date range
        if timeframe == TimeFrame.D1:
            dates = pd.date_range(start, end, freq='D')
        elif timeframe == TimeFrame.H1:
            dates = pd.date_range(start, end, freq='H')
        else:
            dates = pd.date_range(start, end, freq='5T')
            
        # Generate mock OHLCV data
        n = len(dates)
        base_price = 4000  # Example for ES futures
        
        df = pd.DataFrame({
            'open': base_price + np.random.randn(n) * 10,
            'high': base_price + np.random.randn(n) * 10 + 5,
            'low': base_price + np.random.randn(n) * 10 - 5,
            'close': base_price + np.random.randn(n) * 10,
            'volume': np.random.randint(1000, 10000, n)
        }, index=dates)
        
        # Ensure OHLC relationships
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)
        
        return MarketData(
            contract=contract,
            data_type=data_type,
            timestamp=datetime.now(),
            data=df,
            metadata={'source': 'mock', 'timeframe': timeframe.value if timeframe else None}
        )
    
    async def stream_realtime(
        self,
        contract: FuturesContract,
        data_type: DataType,
        callback
    ):
        """Stream mock real-time data."""
        while True:
            # Generate tick data
            tick_data = pd.DataFrame({
                'bid': [4000 + np.random.randn() * 2],
                'ask': [4000.25 + np.random.randn() * 2],
                'bid_size': [np.random.randint(1, 100)],
                'ask_size': [np.random.randint(1, 100)]
            }, index=[pd.Timestamp.now()])
            
            market_data = MarketData(
                contract=contract,
                data_type=DataType.TICK,
                timestamp=datetime.now(),
                data=tick_data
            )
            
            callback(market_data)
            await asyncio.sleep(1)  # Simulate 1 tick per second
    
    def disconnect(self):
        """Disconnect from data source."""
        pass


async def main():
    """Main example function."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # 1. Create futures contracts
    logger.info("Creating futures contracts...")
    
    # E-mini S&P 500 contracts
    es_contracts = [
        FuturesContract(
            symbol="ESH24",  # March 2024
            exchange="CME",
            expiry=datetime(2024, 3, 15),
            multiplier=50.0,
            tick_size=0.25,
            currency="USD",
            timezone="America/Chicago"
        ),
        FuturesContract(
            symbol="ESM24",  # June 2024
            exchange="CME",
            expiry=datetime(2024, 6, 21),
            multiplier=50.0,
            tick_size=0.25,
            currency="USD",
            timezone="America/Chicago"
        ),
        FuturesContract(
            symbol="ESU24",  # September 2024
            exchange="CME",
            expiry=datetime(2024, 9, 20),
            multiplier=50.0,
            tick_size=0.25,
            currency="USD",
            timezone="America/Chicago"
        )
    ]
    
    # Crude Oil futures
    cl_contract = FuturesContract(
        symbol="CLZ24",
        exchange="NYMEX",
        expiry=datetime(2024, 12, 20),
        multiplier=1000.0,
        tick_size=0.01,
        currency="USD",
        timezone="America/New_York"
    )
    
    # 2. Initialize data handler with mock source
    logger.info("Initializing data handler...")
    
    handler = FuturesDataHandler(
        storage_path=Path("./futures_data_example"),
        sources=[MockDataSource()],
        enable_streaming=True,
        enable_validation=True
    )
    
    # 3. Fetch historical data
    logger.info("Fetching historical data...")
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)
    
    historical_data = await handler.fetch_historical_data(
        contracts=es_contracts[:1],  # Just first contract for demo
        data_type=DataType.OHLCV,
        start=start_date,
        end=end_date,
        timeframe=TimeFrame.D1,
        parallel=True
    )
    
    for contract_id, market_data in historical_data.items():
        logger.info(f"Fetched {len(market_data.data)} days of data for {contract_id}")
        logger.info(f"Sample data:\n{market_data.data.head()}")
    
    # 4. Clean and validate data
    logger.info("Cleaning data...")
    
    for contract_id, market_data in historical_data.items():
        # Apply cleaning methods
        cleaned_data = handler.clean_data(
            market_data,
            methods=['remove_duplicates', 'fill_gaps', 'remove_outliers'],
            fill_method='interpolate',
            z_threshold=3
        )
        
        logger.info(f"Cleaned data for {contract_id}")
    
    # 5. Save data in different formats
    logger.info("Saving data...")
    
    for contract_id, market_data in historical_data.items():
        # Save as HDF5
        handler.save_data(market_data, format='hdf5')
        logger.info(f"Saved {contract_id} as HDF5")
        
        # Save as Parquet
        handler.save_data(market_data, format='parquet')
        logger.info(f"Saved {contract_id} as Parquet")
    
    # 6. Load saved data
    logger.info("Loading saved data...")
    
    loaded_data, metadata = handler.load_data(
        key=f"{es_contracts[0].contract_id}_{DataType.OHLCV.value}",
        format='hdf5'
    )
    logger.info(f"Loaded data shape: {loaded_data.shape}")
    logger.info(f"Metadata: {metadata}")
    
    # 7. Timezone conversion
    logger.info("Converting timezones...")
    
    # Convert from Chicago time to UTC
    for contract_id, market_data in historical_data.items():
        utc_data = handler.convert_timezone(market_data, 'UTC')
        logger.info(f"Converted {contract_id} to UTC")
        
        # Convert to Singapore time
        sg_data = handler.convert_timezone(market_data, 'Asia/Singapore')
        logger.info(f"Converted {contract_id} to Singapore time")
    
    # 8. Real-time streaming example (runs for 5 seconds)
    logger.info("Starting real-time data streaming...")
    
    # Define callback for processing streaming data
    def stream_callback(data: MarketData):
        logger.info(f"Received tick: {data.data.iloc[-1].to_dict()}")
    
    # Start streaming
    handler.start_streaming(
        contracts=[es_contracts[0]],
        data_type=DataType.TICK,
        callback=stream_callback
    )
    
    # Let it run for 5 seconds
    await asyncio.sleep(5)
    
    # Stop streaming
    handler.stop_streaming(
        contracts=[es_contracts[0]],
        data_type=DataType.TICK
    )
    
    logger.info("Streaming stopped")
    
    # 9. Build continuous contract (conceptual example)
    logger.info("Building continuous contract...")
    
    # This would typically use real contract data
    # continuous_series = handler.build_continuous_contract(
    #     symbol_pattern='ES',
    #     exchange='CME',
    #     start_date=datetime(2023, 1, 1),
    #     end_date=datetime(2024, 1, 1),
    #     roll_method='volume',
    #     adjustment_method='ratio'
    # )
    
    # 10. Demonstrate timezone-aware trading hours
    logger.info("Filtering to trading hours...")
    
    for contract_id, market_data in historical_data.items():
        # Filter to regular trading hours
        trading_hours_data = TimeZoneHandler.align_to_trading_hours(
            market_data.data,
            exchange='CME',
            session='regular'
        )
        logger.info(f"Filtered {contract_id} to trading hours")
    
    # Cleanup
    handler.shutdown()
    logger.info("Example completed successfully!")


# Utility function to demonstrate data quality checks
def perform_data_quality_checks(data: pd.DataFrame) -> dict:
    """Perform comprehensive data quality checks."""
    checks = {
        'missing_values': data.isnull().sum().to_dict(),
        'duplicates': data.duplicated().sum(),
        'negative_prices': (data[['open', 'high', 'low', 'close']] < 0).any().any(),
        'price_consistency': {
            'high_low_violations': (data['high'] < data['low']).sum(),
            'ohlc_violations': (
                (data['high'] < data[['open', 'close']].max(axis=1)) |
                (data['low'] > data[['open', 'close']].min(axis=1))
            ).sum()
        },
        'volume_stats': {
            'zero_volume_days': (data['volume'] == 0).sum(),
            'avg_volume': data['volume'].mean(),
            'volume_outliers': (
                data['volume'] > data['volume'].mean() + 3 * data['volume'].std()
            ).sum()
        }
    }
    
    return checks


# Utility function for contract specifications
def get_contract_specs(symbol_root: str) -> dict:
    """Get standard contract specifications."""
    specs = {
        'ES': {  # E-mini S&P 500
            'name': 'E-mini S&P 500',
            'exchange': 'CME',
            'multiplier': 50.0,
            'tick_size': 0.25,
            'currency': 'USD',
            'months': ['H', 'M', 'U', 'Z'],  # Mar, Jun, Sep, Dec
            'trading_hours': '17:00-16:00 CT'
        },
        'CL': {  # Crude Oil
            'name': 'Light Sweet Crude Oil',
            'exchange': 'NYMEX',
            'multiplier': 1000.0,
            'tick_size': 0.01,
            'currency': 'USD',
            'months': list('FGHJKMNQUVXZ'),  # All months
            'trading_hours': '18:00-17:00 ET'
        },
        'GC': {  # Gold
            'name': 'Gold',
            'exchange': 'COMEX',
            'multiplier': 100.0,
            'tick_size': 0.10,
            'currency': 'USD',
            'months': ['G', 'J', 'M', 'Q', 'V', 'Z'],  # Feb, Apr, Jun, Aug, Oct, Dec
            'trading_hours': '18:00-17:00 ET'
        },
        'NQ': {  # E-mini NASDAQ-100
            'name': 'E-mini NASDAQ-100',
            'exchange': 'CME',
            'multiplier': 20.0,
            'tick_size': 0.25,
            'currency': 'USD',
            'months': ['H', 'M', 'U', 'Z'],  # Mar, Jun, Sep, Dec
            'trading_hours': '17:00-16:00 CT'
        }
    }
    
    return specs.get(symbol_root, {})


if __name__ == "__main__":
    asyncio.run(main())