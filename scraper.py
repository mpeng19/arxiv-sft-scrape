import requests
import feedparser
import os
import time
import urllib.parse
import random
import argparse
from tqdm import tqdm

def download_arxiv_papers(search_query="operations research", max_articles=None, start=0, max_results=100):
    base_url = "http://export.arxiv.org/api/query?"
    
    if not os.path.exists('pdfs'):
        os.makedirs('pdfs')
    
    article_count = 0
    
    query_params = {
        'search_query': search_query,
        'start': start,
        'max_results': max_results,
        'sortBy': 'relevance',
        'sortOrder': 'descending'
    }
    
    query_string = urllib.parse.urlencode(query_params)
    url = base_url + query_string
    
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Failed to query arXiv API: {response.status_code}")
        return
    
    feed = feedparser.parse(response.content)
    entries = feed.entries
    
    if not entries:
        print(f"No papers found for query: {search_query}")
        return
    
    num_to_download = min(len(entries), max_articles) if max_articles else len(entries)
    pbar = tqdm(total=num_to_download, desc=f"Downloading papers for '{search_query}'")
    
    for entry in entries:
        if max_articles and article_count >= max_articles:
            break
        
        try:
            title = entry.title.replace('\n', ' ').strip()
            arxiv_id = entry.id.split('/abs/')[-1]
            
            pdf_url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"
            
            safe_filename = title.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            safe_filename = safe_filename[:100]
            
            filename = os.path.join('pdfs', f"{safe_filename}.pdf")
            
            pdf_response = requests.get(pdf_url)
            
            if pdf_response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(pdf_response.content)
                article_count += 1
                pbar.update(1)
            else:
                pbar.write(f"Failed to download PDF for '{title}': {pdf_response.status_code}")
            
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            pbar.write(f"Error processing paper: {e}")
    
    pbar.close()
    return article_count

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download research papers from arXiv related to operations research.')
    parser.add_argument('--num_papers', type=int, default=10, help='Number of papers to download per query (default: 10)')
    args = parser.parse_args()
    
    search_queries = [
        "operations research",
    ]
    
    total_downloaded = 0
    
    for query in search_queries:
        downloaded = download_arxiv_papers(search_query=query, max_articles=args.num_papers)
        if downloaded:
            total_downloaded += downloaded
        time.sleep(5)
    
    print(f"\nTotal papers downloaded: {total_downloaded}")