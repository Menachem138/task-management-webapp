import asyncio
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_run.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from test_cases import run_test_cases

async def main():
    try:
        logger.info("Starting test suite...")
        results = await run_test_cases('7099400053:AAGpkQ978uhK1M3GnFwNoNH04QyNVb4ufsk')
        
        # Print results with categories
        categories = {
            'Start Command': [r for r in results if 'Start command' in r.name],
            'Search Tests': [r for r in results if 'Search' in r.name],
            'Audio Tests': [r for r in results if 'Audio' in r.name],
            'Error Handling': [r for r in results if 'Error' in r.name]
        }
        
        print('\nTest Results:')
        print('=' * 60)
        
        for category, tests in categories.items():
            if tests:
                print(f'\n{category}:')
                print('-' * 40)
                for result in tests:
                    status = '✓' if result.passed else '✗'
                    print(f'{status} {result.name}')
                    if not result.passed and result.error:
                        print(f'   Error: {result.error}')
        
        print('\n' + '=' * 60)
        
        # Calculate summary with categories
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        category_stats = {
            cat: f"{sum(1 for r in tests if r.passed)}/{len(tests)}"
            for cat, tests in categories.items()
            if tests
        }
        
        print('\nCategory Summary:')
        for cat, stats in category_stats.items():
            print(f'{cat}: {stats} passed')
        
        print(f'\nOverall: {passed}/{total} tests passed')
        
        # Exit with appropriate status code
        if passed < total:
            logger.error("Some tests failed")
            sys.exit(1)
        
        logger.info("All tests passed successfully")
        
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
