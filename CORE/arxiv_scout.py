import urllib.request, urllib.parse, xml.etree.ElementTree as ET, sys, ssl

def search_arxiv(q):
    words = [w for w in q.strip().split() if len(w) > 2]
    boolean_q = "+AND+".join(f"all:{urllib.parse.quote(w)}" for w in words) or "all:algorithm"
    base = "https://export." + "arxiv.org/api/" + "query"
    url = f"{base}?search_query={boolean_q}&start=0&max_results=3&sortBy=relevance"
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    xml_data = urllib.request.urlopen(req, timeout=15, context=ctx).read()
    root = ET.fromstring(xml_data)
    ns = {"a": "http://www." + "w3.org/2005/" + "Atom"}
    results = []
    for entry in root.findall("a:entry", ns):
        title = entry.find("a:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("a:summary", ns).text.strip().replace("\n", " ")[:320]
        link = entry.find("a:id", ns).text.strip()
        results.append(f"- **{title}** ({link}): {summary}...")
    return results

query = " ".join(sys.argv[1:]).strip() or "streaming data aggregation"
try:
    res = search_arxiv(query)
    if not res:
        res = search_arxiv("agent self improvement")
    print("\n".join(res) if res else "NO_PAPERS_FOUND")
except Exception as e:
    print(f"ARXIV_ERROR: {e}")
