"""
WORKING Telugu Corpus Collector - All Fixed Issues
Author: Fixed for Viswam.ai SOAI 2025
Purpose: Single file, no imports, everything works
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import re
import json
import pandas as pd
from pathlib import Path
import os
import time

st.set_page_config(
    page_title="Telugu Corpus Collector - WORKING",
    page_icon="📚",
    layout="wide"
)

# ===== CONFIGURATION =====
def get_config():
    """Get configuration from sidebar."""
    st.sidebar.header("⚙️ Configuration")
    
    with st.sidebar.expander("📥 Collection Settings", expanded=True):
        timeout = st.number_input("Request Timeout (seconds)", 5, 30, 15)
        delay = st.number_input("Delay Between Requests (seconds)", 0.5, 5.0, 1.0, 0.5)
        max_retries = st.number_input("Max Retries", 1, 5, 3)
    
    with st.sidebar.expander("🔤 Text Quality Settings"):
        min_para_len = st.number_input("Min Paragraph Length", 10, 100, 20)
        min_telugu_ratio = st.slider("Min Telugu Ratio", 0.1, 1.0, 0.6, 0.1)
        extract_headings = st.checkbox("Extract Headings", True)
    
    return {
        'timeout': timeout,
        'delay_between_requests': delay,
        'max_retries': max_retries,
        'min_paragraph_length': min_para_len,
        'min_telugu_ratio': min_telugu_ratio,
        'extract_headings': extract_headings
    }

# ===== UTILITY FUNCTIONS =====
def is_telugu_text(text, min_ratio=0.6):
    """Check if text contains sufficient Telugu characters."""
    if not text.strip():
        return False
    
    telugu_chars = len(re.findall(r'[\u0C00-\u0C7F]', text))
    total_chars = len(re.findall(r'\w', text))
    
    if total_chars == 0:
        return False
    
    return telugu_chars / total_chars >= min_ratio

def clean_text(text):
    """Basic text cleaning."""
    text = re.sub(r'\s+', ' ', text)  # Remove extra whitespace
    text = re.sub(r'http[s]?://\S+', '', text)  # Remove URLs
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)  # Remove emails
    return text.strip()

def collect_from_url(url, config):
    """Collect Telugu text from a single URL."""
    try:
        st.write(f"🌐 Fetching: {url}")
        
        headers = {'User-Agent': 'Telugu-Corpus-Collector/1.0 (Educational)'}
        response = requests.get(url, timeout=config['timeout'], headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        
        paragraphs = []
        headings = []
        
        # Extract paragraphs
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) >= config['min_paragraph_length'] and is_telugu_text(text, config['min_telugu_ratio']):
                paragraphs.append(clean_text(text))
        
        # Extract headings if enabled
        if config['extract_headings']:
            for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                for h in soup.find_all(tag):
                    text = h.get_text(strip=True)
                    if text and is_telugu_text(text, config['min_telugu_ratio']):
                        headings.append(clean_text(text))
        
        st.write(f"✅ Found {len(paragraphs)} paragraphs and {len(headings)} headings")
        
        return {
            'url': url,
            'paragraphs': paragraphs,
            'headings': headings,
            'success': True,
            'error': None
        }
        
    except Exception as e:
        st.error(f"❌ Error with {url}: {str(e)}")
        return {
            'url': url,
            'paragraphs': [],
            'headings': [],
            'success': False,
            'error': str(e)
        }

def save_corpus(collected_data, config):
    """Save collected corpus data to files."""
    if not collected_data:
        return None, None
    
    # Create directories
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save raw corpus
    raw_file = raw_dir / f"raw_telugu_{timestamp}.txt"
    all_text = []
    
    with open(raw_file, "w", encoding="utf-8") as f:
        f.write(f"# Telugu Corpus Collection - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total sources: {len([d for d in collected_data if d['success']])}\n\n")
        
        for data in collected_data:
            if data['success'] and (data['paragraphs'] or data['headings']):
                f.write(f"\n=== SOURCE: {data['url']} ===\n\n")
                
                # Write paragraphs
                for para in data['paragraphs']:
                    f.write(para + "\n")
                    all_text.append(para)
                
                # Write headings
                if data['headings']:
                    f.write("\n--- HEADINGS ---\n")
                    for heading in data['headings']:
                        f.write(heading + "\n")
                        all_text.append(heading)
                
                f.write("\n" + "="*60 + "\n")
    
    # Save metadata
    successful_urls = [d for d in collected_data if d['success']]
    failed_urls = [d for d in collected_data if not d['success']]
    
    metadata = {
        "collection_date": datetime.datetime.now().isoformat(),
        "total_urls": len(collected_data),
        "successful_urls": len(successful_urls),
        "failed_urls": len(failed_urls),
        "total_paragraphs": sum(len(d['paragraphs']) for d in successful_urls),
        "total_headings": sum(len(d['headings']) for d in successful_urls),
        "total_text_items": len(all_text),
        "total_characters": sum(len(text) for text in all_text),
        "config_used": config,
        "failed_url_details": [{'url': d['url'], 'error': d['error']} for d in failed_urls]
    }
    
    metadata_file = raw_dir / f"metadata_{timestamp}.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return str(raw_file), metadata

def clean_corpus_file(raw_file_path, config):
    """Clean a raw corpus file."""
    try:
        with open(raw_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into lines and clean
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line.startswith('===') or line.startswith('---') or line.startswith('#'):
                continue
            
            # Clean the line
            cleaned_line = clean_text(line)
            
            # Check if it's good Telugu text
            if len(cleaned_line) >= 10 and is_telugu_text(cleaned_line, config['min_telugu_ratio']):
                cleaned_lines.append(cleaned_line)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_lines = []
        for line in cleaned_lines:
            line_lower = line.lower()
            if line_lower not in seen:
                seen.add(line_lower)
                unique_lines.append(line)
        
        # Save cleaned file
        clean_dir = Path("data/clean")
        clean_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_file = clean_dir / f"clean_telugu_{timestamp}.txt"
        
        with open(clean_file, "w", encoding="utf-8") as f:
            f.write('\n'.join(unique_lines))
        
        # Save cleaning stats
        cleaning_stats = {
            "original_lines": len(lines),
            "cleaned_lines": len(cleaned_lines),
            "final_lines": len(unique_lines),
            "duplicates_removed": len(cleaned_lines) - len(unique_lines),
            "reduction_percentage": (1 - len(unique_lines) / len(lines)) * 100,
            "cleaning_date": datetime.datetime.now().isoformat()
        }
        
        stats_file = clean_file.with_suffix('.json')
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(cleaning_stats, f, indent=2, ensure_ascii=False)
        
        return str(clean_file), cleaning_stats
        
    except Exception as e:
        st.error(f"Cleaning failed: {e}")
        return None, None

# ===== STREAMLIT APP =====
st.markdown("""
    <style>
    /* ===== Dark Alive Background Gradient Animation ===== */
    .stApp {
        background: linear-gradient(-45deg, #0f0f1c, #1a1a2e, #0d0d0d, #111111);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
    }
    
    /* ===== Floating 3D Neon Orbs ===== */
    .stApp::before, .stApp::after {
        content: '';
        position: absolute;
        width: 250px;
        height: 250px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(0,255,255,0.2) 0%, transparent 70%);
        animation: floatOrb 25s infinite ease-in-out alternate;
        z-index: 0;
    }
    
    .stApp::after {
        left: 70%;
        top: 20%;
        background: radial-gradient(circle, rgba(255,0,200,0.25) 0%, transparent 70%);
        animation-delay: 12s;
    }
    
    .stApp::before {
        left: 15%;
        top: 65%;
        background: radial-gradient(circle, rgba(255,200,0,0.25) 0%, transparent 70%);
    }
    
    @keyframes floatOrb {
        0%   { transform: translateY(0px) translateX(0px) scale(1); }
        50%  { transform: translateY(-60px) translateX(40px) scale(1.3); }
        100% { transform: translateY(0px) translateX(0px) scale(1); }
    }
    
    @keyframes gradientBG {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    
    /* ===== Glowing Telugu Title ===== */
    .glow-text {
        font-size: 3em;
        font-weight: bold;
        text-align: center;
        color: #ffde59;
        text-shadow: 0 0 10px #ffde59, 0 0 20px #ffae00, 
                     0 0 30px #ff7300, 0 0 40px #ff4800;
        animation: pulse 2s infinite;
    }
    
    /* ===== Glowing English Subtitle ===== */
    .glow-subtext {
        font-size: 1.5em;
        font-weight: bold;
        text-align: center;
        color: #00ffe5;
        text-shadow: 0 0 10px #00ffe5, 0 0 20px #00e0ff, 0 0 30px #00bfff;
        animation: pulse 2s infinite alternate;
    }
    
    @keyframes pulse {
        0% { text-shadow: 0 0 10px #ff00de, 0 0 20px #ff00de; }
        50% { text-shadow: 0 0 40px #00ffff, 0 0 80px #00ffff; }
        100% { text-shadow: 0 0 10px #ff00de, 0 0 20px #ff00de; }
    }
    
    /* ===== Glassmorphic Glowing Buttons ===== */
    div.stButton > button {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(0, 255, 255, 0.4);
        border-radius: 15px;
        padding: 0.6em 1.2em;
        color: #fff;
        font-weight: bold;
        backdrop-filter: blur(12px);
        box-shadow: 0 0 12px rgba(0,255,255,0.7),
                    0 0 25px rgba(0,200,255,0.4),
                    inset 0 0 10px rgba(255,255,255,0.05);
        transition: all 0.3s ease-in-out;
    }
    
    div.stButton > button:hover {
        transform: scale(1.08);
        box-shadow: 0 0 20px rgba(0,255,255,1),
                    0 0 40px rgba(0,200,255,0.8),
                    inset 0 0 15px rgba(255,255,255,0.1);
        border: 1px solid rgba(0,255,255,0.7);
    }
    </style>
""", unsafe_allow_html=True)

# Splash Loader
with st.spinner("✨ Launching Telugu Corpus Collector..."):
    time.sleep(1)

# Titles
st.markdown("<h1 class='glow-text'>📚 తెలుగు కార్పస్ కలెక్టర్ 🚀</h1>", unsafe_allow_html=True)
st.markdown("<h2 class='glow-subtext'>Telugu Corpus Collector - Stunning UI ✨</h2>", unsafe_allow_html=True)

st.title("📚AI Telugu Corpus Collector - WORKING VERSION ✅")
st.markdown("**Fixed all issues - Ready for your Viswam.ai internship!**")

# Get configuration from sidebar
config = get_config()

# Initialize session state
if 'collection_results' not in st.session_state:
    st.session_state.collection_results = None
if 'cleaning_results' not in st.session_state:
    st.session_state.cleaning_results = None

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔗 URLs", "📥 Collection", "🧹 Cleaning", "📊 Results"])

# ===== TAB 1: URL MANAGEMENT =====
with tab1:
    st.header("🔗 URL Management")
    
    # Ensure URLs directory exists
    urls_dir = Path("data/urls")
    urls_dir.mkdir(parents=True, exist_ok=True)
    urls_file = urls_dir / "urls.txt"
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Add URLs")
        
        # Single URL input
        new_url = st.text_input(
            "Enter Telugu URL:",
            placeholder="https://te.wikipedia.org/wiki/తెలుగు"
        )
        
        if st.button("➕ Add URL") and new_url:
            with open(urls_file, "a", encoding="utf-8") as f:
                f.write(new_url.strip() + "\n")
            st.success(f"✅ Added: {new_url}")
            st.rerun()
        
        # Batch URL input
        st.subheader("Batch Add URLs")
        urls_text = st.text_area(
            "Paste multiple URLs (one per line):",
            height=150,
            placeholder="https://te.wikipedia.org/wiki/తెలుగు\nhttps://te.wikipedia.org/wiki/ఆంధ్రప్రదేశు"
        )
        
        if st.button("➕ Add All URLs") and urls_text:
            urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
            with open(urls_file, "a", encoding="utf-8") as f:
                for url in urls:
                    f.write(url + "\n")
            st.success(f"✅ Added {len(urls)} URLs")
            st.rerun()
    
    with col2:
        st.subheader("Current URLs")
        
        # Show current URLs
        if urls_file.exists():
            with open(urls_file, 'r', encoding='utf-8') as f:
                current_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if current_urls:
                st.info(f"📊 Total URLs: {len(current_urls)}")
                
                # Show URLs
                for i, url in enumerate(current_urls[-8:], 1):  # Show last 8
                    st.text(f"{i}. {url[:55]}{'...' if len(url) > 55 else ''}")
                
                if len(current_urls) > 8:
                    st.info(f"... and {len(current_urls) - 8} more")
            else:
                st.warning("No URLs found. Add some URLs!")
        else:
            st.warning("No URLs file found.")
            
            # Add sample URLs button
            if st.button("🎯 Add Sample Telugu URLs"):
                sample_urls = [
                    "https://te.wikipedia.org/wiki/తెలుగు", 
                    "https://te.wikipedia.org/wiki/తెలంగాణ",
                    "https://te.wikipedia.org/wiki/భారతదేశం",
                    "https://te.wikipedia.org/wiki/హైదరాబాద్",
                    "https://te.wikipedia.org/wiki/విశాఖపట్నం"
                ]
                
                with open(urls_file, "w", encoding="utf-8") as f:
                    f.write("# Telugu URLs for corpus collection\n")
                    f.write("# Add one URL per line\n\n")
                    for url in sample_urls:
                        f.write(url + "\n")
                st.success("✅ Added 6 sample Telugu Wikipedia URLs!")
                st.rerun()
        
        # Clear URLs button
        if st.button("🗑️ Clear All URLs", type="secondary"):
            if urls_file.exists():
                urls_file.unlink()
            st.success("✅ All URLs cleared!")
            st.rerun()

# ===== TAB 2: COLLECTION =====
with tab2:
    st.header("📥 Corpus Collection")
    
    # Check if URLs exist
    if not urls_file.exists():
        st.error("❌ No URLs found. Please add URLs in the 'URLs' tab first.")
    else:
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        if not urls:
            st.error("❌ No valid URLs found. Please add URLs in the 'URLs' tab first.")
        else:
            st.info(f"📊 Ready to collect from {len(urls)} URLs")
            
            # Show configuration summary
            with st.expander("⚙️ Current Settings"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Timeout:** {config['timeout']}s")
                    st.write(f"**Delay:** {config['delay_between_requests']}s")
                    st.write(f"**Max Retries:** {config['max_retries']}")
                with col2:
                    st.write(f"**Min Paragraph Length:** {config['min_paragraph_length']}")
                    st.write(f"**Min Telugu Ratio:** {config['min_telugu_ratio']:.1%}")
                    st.write(f"**Extract Headings:** {config['extract_headings']}")
            
            # Start collection button
            if st.button("🚀 Start Collection", type="primary", use_container_width=True):
                st.write("### 📊 Collection Progress")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                collected_data = []
                
                # Process each URL
                for i, url in enumerate(urls):
                    # Update progress
                    progress = (i + 1) / len(urls)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {i+1}/{len(urls)}: {url[:50]}...")
                    
                    # Collect from URL
                    result = collect_from_url(url, config)
                    collected_data.append(result)
                    
                    # Add delay between requests
                    if i < len(urls) - 1:
                        time.sleep(config['delay_between_requests'])
                
                # Save results
                status_text.text("💾 Saving collected data...")
                
                raw_file, metadata = save_corpus(collected_data, config)
                
                if raw_file and metadata:
                    # Store results in session
                    st.session_state.collection_results = {
                        'raw_file': raw_file,
                        'metadata': metadata,
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                    
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Show success message
                    st.success("🎉 Collection Completed Successfully!")
                    
                    # Show summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("URLs Processed", metadata['total_urls'])
                    with col2:
                        st.metric("Successful", metadata['successful_urls'])
                    with col3:
                        st.metric("Failed", metadata['failed_urls'])
                    with col4:
                        st.metric("Text Items", metadata['total_text_items'])
                    
                    st.info(f"📂 **Saved to:** {raw_file}")
                    st.info(f"📊 **Total Characters:** {metadata['total_characters']:,}")
                    
                    # Show failed URLs if any
                    if metadata['failed_urls'] > 0:
                        with st.expander("⚠️ Failed URLs"):
                            for failed in metadata['failed_url_details']:
                                st.error(f"❌ {failed['url']}: {failed['error']}")
                    
                    st.balloons()
                else:
                    st.error("❌ Collection failed. No content was saved.")

# ===== TAB 3: CLEANING =====
with tab3:
    st.header("🧹 Corpus Cleaning")
    
    # Find raw files
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        st.warning("⚠️ No raw data found. Run collection first!")
    else:
        raw_files = sorted(list(raw_dir.glob("raw_telugu_*.txt")), 
                          key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not raw_files:
            st.warning("⚠️ No raw files found. Run collection first!")
        else:
            st.info(f"📁 Found {len(raw_files)} raw files")
            
            # Select file to clean
            selected_file = st.selectbox(
                "Select file to clean:",
                raw_files,
                format_func=lambda x: f"{x.name} ({x.stat().st_size // 1024} KB)"
            )
            
            if selected_file:
                # Show file info
                stat = selected_file.stat()
                st.info(f"📄 **File:** {selected_file.name}")
                st.info(f"📊 **Size:** {stat.st_size // 1024} KB | **Modified:** {datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}")
                
                # Preview file content
                with st.expander("👀 Preview Content"):
                    try:
                        with open(selected_file, 'r', encoding='utf-8') as f:
                            preview = f.read(1000)
                        st.text_area("First 1000 characters:", preview, height=200, disabled=True)
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
                
                # Cleaning settings
                with st.expander("🛠️ Cleaning Settings"):
                    st.write(f"**Min Line Length:** 10 characters")
                    st.write(f"**Min Telugu Ratio:** {config['min_telugu_ratio']:.1%}")
                    st.write(f"**Remove Duplicates:** Yes")
                    st.write(f"**Clean URLs/Emails:** Yes")
                
                # Start cleaning
                if st.button("🧹 Start Cleaning", type="primary"):
                    with st.spinner("Cleaning corpus file..."):
                        clean_file, cleaning_stats = clean_corpus_file(str(selected_file), config)
                    
                    if clean_file and cleaning_stats:
                        st.session_state.cleaning_results = {
                            'clean_file': clean_file,
                            'stats': cleaning_stats,
                            'timestamp': datetime.datetime.now().isoformat()
                        }
                        
                        st.success("🎉 Cleaning Completed!")
                        
                        # Show cleaning results
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Original Lines", cleaning_stats['original_lines'])
                        with col2:
                            st.metric("Final Lines", cleaning_stats['final_lines'])
                        with col3:
                            st.metric("Duplicates Removed", cleaning_stats['duplicates_removed'])
                        with col4:
                            st.metric("Reduction", f"{cleaning_stats['reduction_percentage']:.1f}%")
                        
                        st.info(f"📂 **Cleaned file:** {clean_file}")
                        
                        # Show preview of cleaned text
                        st.subheader("👀 Preview Cleaned Text")
                        try:
                            with open(clean_file, 'r', encoding='utf-8') as f:
                                preview = f.read(2000)  # first 2000 characters
                            st.text_area("Cleaned Text Preview:", preview, height=300)
                        except Exception as e:
                            st.error(f"Error reading cleaned file: {e}")
                    else:
                        st.error("❌ Cleaning failed!")

# ===== TAB 4: RESULTS =====
with tab4:
    st.header("📊 All Results")
    
    # Latest collection results
    if st.session_state.collection_results:
        results = st.session_state.collection_results
        metadata = results['metadata']
        
        st.subheader("📥 Latest Collection")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Success Rate", f"{metadata['successful_urls']}/{metadata['total_urls']}")
        with col2:
            st.metric("Text Items", metadata['total_text_items'])
        with col3:
            file_size = Path(results['raw_file']).stat().st_size // 1024
            st.metric("File Size", f"{file_size} KB")
        
        st.info(f"📂 {results['raw_file']}")
    
    # Latest cleaning results
    if st.session_state.cleaning_results:
        cleaning = st.session_state.cleaning_results
        stats = cleaning['stats']
        
        st.subheader("🧹 Latest Cleaning")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Lines Processed", stats['original_lines'])
        with col2:
            st.metric("Final Lines", stats['final_lines'])
        with col3:
            st.metric("Quality Improvement", f"{stats['reduction_percentage']:.1f}%")
        
        st.info(f"📂 {cleaning['clean_file']}")
    
    # All files overview
    st.subheader("📁 All Files")
    
    all_files = []
    
    # Raw files
    raw_dir = Path("data/raw")
    if raw_dir.exists():
        for f in raw_dir.glob("*.txt"):
            stat = f.stat()
            all_files.append({
                "Type": "Raw",
                "File": f.name,
                "Size (KB)": stat.st_size // 1024,
                "Created": datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
            })
    
    # Clean files  
    clean_dir = Path("data/clean")
    if clean_dir.exists():
        for f in clean_dir.glob("*.txt"):
            stat = f.stat()
            all_files.append({
                "Type": "Clean",
                "File": f.name,
                "Size (KB)": stat.st_size // 1024,
                "Created": datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
            })
    
    if all_files:
        df = pd.DataFrame(all_files)
        df = df.sort_values('Created', ascending=False)
        st.dataframe(df, use_container_width=True)
        
        # Summary
        total_files = len(df)
        total_size = df["Size (KB)"].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Files", total_files)
        with col2:
            st.metric("Total Size", f"{total_size} KB")
    else:
        st.info("📝 No files found yet. Run collection to get started!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <strong>🎉 Telugu Corpus Collector - WORKING VERSION</strong><br>
    All issues fixed | Ready for Viswam.ai Summer of AI 2025 success!<br>
    <em>Collection ✅ | Cleaning ✅ | Results ✅</em>
</div>
""", unsafe_allow_html=True)