"""
Analytics Module Demo

This script demonstrates the usage of the portfolio analytics and reporting module.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pathlib import Path

# Import analytics module
import sys
sys.path.append('../src')
from claude_sdk.analytics import (
    PortfolioAnalytics, 
    PortfolioVisualizer, 
    ReportGenerator,
    EmailNotifier
)


def generate_sample_data():
    """Generate sample portfolio data for demonstration"""
    # Generate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*2)  # 2 years of data
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Generate returns with some realistic characteristics
    np.random.seed(42)
    
    # Base returns with trend and volatility
    trend = 0.0001  # Small positive drift
    volatility = 0.015  # 1.5% daily volatility
    
    returns = np.random.normal(trend, volatility, len(dates))
    
    # Add some autocorrelation (momentum)
    for i in range(1, len(returns)):
        returns[i] = 0.1 * returns[i-1] + 0.9 * returns[i]
    
    # Create returns series
    returns_series = pd.Series(returns, index=dates, name='returns')
    
    # Generate sample trades
    n_trades = 100
    trade_dates = np.random.choice(dates[:-5], n_trades, replace=False)
    trade_dates.sort()
    
    trades = []
    for i, entry_date in enumerate(trade_dates):
        # Random holding period (1-20 days)
        holding_days = np.random.randint(1, 20)
        exit_date = entry_date + timedelta(days=holding_days)
        
        # Random return for the trade
        trade_return = np.random.normal(0.002, 0.03)
        
        trades.append({
            'trade_id': i,
            'entry_date': entry_date,
            'exit_date': exit_date,
            'entry_value': 10000,
            'exit_value': 10000 * (1 + trade_return),
            'pnl': 10000 * trade_return,
            'return': trade_return,
            'duration': holding_days,
            'asset': np.random.choice(['AAPL', 'GOOGL', 'MSFT', 'AMZN']),
            'sector': np.random.choice(['Technology', 'Consumer', 'Healthcare'])
        })
    
    trades_df = pd.DataFrame(trades)
    
    # Generate benchmark returns (market index)
    benchmark_returns = np.random.normal(0.00005, 0.012, len(dates))
    benchmark_series = pd.Series(benchmark_returns, index=dates, name='benchmark')
    
    # Generate position data
    positions = []
    for date in dates[::5]:  # Every 5 days
        for asset in ['AAPL', 'GOOGL', 'MSFT', 'AMZN']:
            positions.append({
                'date': date,
                'asset': asset,
                'weight': np.random.uniform(0.1, 0.4),
                'return': np.random.normal(0.0001, 0.02),
                'sector': 'Technology'
            })
    
    positions_df = pd.DataFrame(positions)
    
    return returns_series, trades_df, positions_df, benchmark_series


def main():
    """Main demo function"""
    print("Portfolio Analytics Demo")
    print("=" * 50)
    
    # Generate sample data
    print("\n1. Generating sample portfolio data...")
    returns, trades, positions, benchmark = generate_sample_data()
    print(f"   - Generated {len(returns)} days of return data")
    print(f"   - Generated {len(trades)} trades")
    print(f"   - Generated {len(positions)} position records")
    
    # Initialize analytics
    print("\n2. Initializing analytics engine...")
    analytics = PortfolioAnalytics(
        returns=returns,
        positions=positions,
        trades=trades,
        benchmark_returns=benchmark,
        risk_free_rate=0.02
    )
    
    # Calculate performance metrics
    print("\n3. Calculating performance metrics...")
    metrics = analytics.calculate_performance_metrics()
    
    print("\nKey Performance Metrics:")
    print(f"   - Total Return: {metrics.total_return:.2%}")
    print(f"   - Annualized Return: {metrics.annualized_return:.2%}")
    print(f"   - Volatility: {metrics.volatility:.2%}")
    print(f"   - Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"   - Max Drawdown: {metrics.max_drawdown:.2%}")
    print(f"   - Win Rate: {metrics.win_rate:.2%}")
    print(f"   - Total Trades: {metrics.total_trades}")
    
    # Perform additional analysis
    print("\n4. Performing additional analysis...")
    
    # Win/loss streaks
    streak_analysis = analytics.analyze_win_loss_streaks()
    print(f"\nStreak Analysis:")
    print(f"   - Max Win Streak: {streak_analysis['max_win_streak']}")
    print(f"   - Max Loss Streak: {streak_analysis['max_loss_streak']}")
    
    # Best/worst trades
    best_worst = analytics.identify_best_worst_trades(n=5)
    print(f"\nTop 5 Best Trades:")
    for _, trade in best_worst['best_trades'].iterrows():
        print(f"   - {trade['asset']}: {trade['return']:.2%} ({trade['duration']} days)")
    
    # Trade duration stats
    duration_stats = analytics.calculate_trade_duration_stats()
    print(f"\nTrade Duration Statistics:")
    print(f"   - Average: {duration_stats['avg_duration']:.1f} days")
    print(f"   - Median: {duration_stats['median_duration']:.1f} days")
    
    # Initialize visualizer
    print("\n5. Creating visualizations...")
    visualizer = PortfolioVisualizer(analytics)
    
    # Create output directory
    output_dir = Path("analytics_output")
    output_dir.mkdir(exist_ok=True)
    
    # Generate charts
    charts = {
        'equity_curve': visualizer.plot_equity_curve(benchmark=True),
        'drawdown': visualizer.plot_drawdown(),
        'return_dist': visualizer.plot_return_distribution(),
        'risk_return': visualizer.plot_risk_return_scatter(),
        'dashboard': visualizer.create_performance_dashboard()
    }
    
    # Save charts
    for name, fig in charts.items():
        path = output_dir / f"{name}.png"
        fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f"   - Saved {name} chart to {path}")
        plt.close(fig)
    
    # Generate reports
    print("\n6. Generating reports...")
    report_gen = ReportGenerator(analytics, visualizer)
    
    # PDF report
    pdf_path = output_dir / "portfolio_report.pdf"
    report_gen.generate_pdf_report(str(pdf_path), report_type='comprehensive')
    print(f"   - Generated PDF report: {pdf_path}")
    
    # JSON report
    json_path = output_dir / "portfolio_report.json"
    report_gen.generate_json_report(str(json_path))
    print(f"   - Generated JSON report: {json_path}")
    
    # Dashboard data
    dashboard_data = report_gen.prepare_dashboard_data()
    print(f"\n7. Dashboard data prepared with {len(dashboard_data)} sections")
    
    # Email notification example (disabled by default)
    email_demo = False
    if email_demo:
        print("\n8. Setting up email notifications...")
        notifier = EmailNotifier(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="your_email@gmail.com",
            password="your_password"
        )
        
        # Send report
        success = notifier.send_report(
            recipient="recipient@example.com",
            subject="Portfolio Performance Report",
            body=notifier.create_performance_summary_html(analytics),
            attachments=[str(pdf_path)]
        )
        print(f"   - Email sent: {success}")
    
    print("\n" + "=" * 50)
    print("Demo completed successfully!")
    print(f"All outputs saved to: {output_dir.absolute()}")


if __name__ == "__main__":
    main()