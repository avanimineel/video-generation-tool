import os
import sys
import json
import requests
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import reload_env, settings
from app.services.media_providers.pexels import PexelsProvider
from app.services.media_providers.pixabay import PixabayProvider
from app.services.media_search_service import media_search_service
from app.services.asset_downloader import asset_downloader

def run_diagnostics():
    reload_env()
    print('='*70)
    print('MEDIA ACQUISITION DIAGNOSTIC TEST SUITE')
    print('='*70)

    # 1. Verify environment variables
    pexels_key = os.environ.get('PEXELS_API_KEY')
    pixabay_key = os.environ.get('PIXABAY_API_KEY')
    
    print()
    print('[1] ENVIRONMENT VARIABLE VERIFICATION:')
    print(f'  PEXELS_API_KEY loaded:  {bool(pexels_key)} (Masked: {pexels_key[:4] + "..." + pexels_key[-3:] if pexels_key and len(pexels_key)>7 else "Not configured"})')
    print(f'  PIXABAY_API_KEY loaded: {bool(pixabay_key)} (Masked: {pixabay_key[:4] + "..." + pixabay_key[-3:] if pixabay_key and len(pixabay_key)>7 else "Not configured"})')
    
    # 2. Provider connections
    pexels = PexelsProvider()
    pixabay = PixabayProvider()
    
    print()
    print('[2] SERVER-SIDE PROVIDER CONNECTION TESTS:')
    print('  Testing Pexels connection...')
    pexels_conn = pexels.check_connection()
    print(f'  Pexels Connection Result:  HTTP {pexels_conn.get("http_code")} | Status: {pexels_conn.get("status")} | Message: {pexels_conn.get("message")}')
    
    print('  Testing Pixabay connection...')
    pixabay_conn = pixabay.check_connection()
    print(f'  Pixabay Connection Result: HTTP {pixabay_conn.get("http_code")} | Status: {pixabay_conn.get("status")} | Message: {pixabay_conn.get("message")}')

    # 3. Target project for download verification
    project_id = 'proj_sub_1789413464499'
    download_dir = settings.projects_dir / project_id / 'media' / 'downloaded'
    download_dir.mkdir(parents=True, exist_ok=True)
    print()
    print(f'[3] LOCAL STORAGE TARGET: {download_dir}')

    # Exact tests to run
    test_cases = [
        {
            'name': 'Test 1: Pexels image search',
            'provider': 'pexels',
            'query': 'doctor hospital',
            'media_type': 'image',
            'method': pexels.search_images
        },
        {
            'name': 'Test 2: Pexels video search',
            'provider': 'pexels',
            'query': 'hospital corridor',
            'media_type': 'video',
            'method': pexels.search_videos
        },
        {
            'name': 'Test 3: Pixabay image search',
            'provider': 'pixabay',
            'query': 'breast cancer awareness',
            'media_type': 'image',
            'method': pixabay.search_images
        },
        {
            'name': 'Test 4: Pixabay video search',
            'provider': 'pixabay',
            'query': 'hospital patient',
            'media_type': 'video',
            'method': pixabay.search_videos
        }
    ]

    results_report = []

    print()
    print('='*70)
    print('EXECUTING 4 REQUIRED LIVE SEARCH & DOWNLOAD TESTS')
    print('='*70)

    for tc in test_cases:
        print()
        print(f'>>> {tc["name"]}: "{tc["query"]}"')
        
        # Execute server-side search
        hits = tc['method'](tc['query'], limit=4)
        diag = getattr(tc['method'].__self__, 'last_diagnostic', {})
        http_status = diag.get('http_code')
        result_count = len(hits)
        
        print(f'  - HTTP Status: {http_status}')
        print(f'  - Number of results: {result_count}')
        
        example_obj = None
        local_saved_path = None
        file_size_bytes = 0

        if hits:
            sample_asset = hits[0]
            example_obj = sample_asset.to_dict()
            print(f'  - Example Result Title: "{sample_asset.title}"')
            print(f'  - Example Thumb URL: {sample_asset.thumb_url[:70]}...')
            print(f'  - Example Download URL: {sample_asset.download_url[:70]}...')
            
            # Download asset locally
            try:
                download_res = asset_downloader.download_asset(project_id, example_obj)
                local_saved_path = download_res.get('local_path')
                if local_saved_path and os.path.exists(local_saved_path):
                    file_size_bytes = os.path.getsize(local_saved_path)
                    print(f'  - Local saved file path: {local_saved_path}')
                    print(f'  - File size on disk: {file_size_bytes:,} bytes')
            except Exception as e:
                print(f'  - Download error: {e}')
        else:
            print(f'  - Diagnostic Details: {diag.get("error") or diag.get("message")}')
            print('  - Asset Download: Skipped (0 hits returned by unauthenticated API)')

        results_report.append({
            'test': tc['name'],
            'query': tc['query'],
            'provider': tc['provider'],
            'media_type': tc['media_type'],
            'http_status': http_status,
            'result_count': result_count,
            'example_result': example_obj,
            'local_file_path': local_saved_path,
            'file_size_bytes': file_size_bytes,
            'diagnostic': diag
        })

    # 4. Also test the full waterfall search endpoint via MediaSearchService
    print()
    print('='*70)
    print('VERIFYING WATERFALL PRIORITY CHAIN (1. Pexels -> 2. Pixabay -> 3. Stock -> 4. Wiki)')
    print('='*70)
    waterfall_res = media_search_service.search_media("doctor hospital", media_type="image", provider="all", limit=4)
    waterfall_diag = getattr(media_search_service, 'last_search_diagnostics', {})
    print(f'  Waterfall Result Count: {len(waterfall_res)}')
    print(f'  Waterfall Step Satisfied: {waterfall_diag.get("waterfall_step")}')
    print(f'  Provider Used: {waterfall_diag.get("provider_used")}')
    print(f'  Waterfall Provider Attempts: {waterfall_diag.get("attempts")}')

    # Output JSON summary for logging
    with open('test_diagnostic_report.json', 'w') as out_f:
        json.dump(results_report, out_f, indent=2)
    print()
    print('Full diagnostic report written to backend/test_diagnostic_report.json')

if __name__ == '__main__':
    run_diagnostics()
