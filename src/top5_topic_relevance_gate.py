"""Conservative keyword filter. This is NOT visual recognition or a 75-point score."""
import re
STOP={"top","best","amazing","funny","beautiful","satisfying","moment","moments","slow","motion","reaction","playing","play","close","up","macro","video","videos","nature","people","human","animal","animals","outdoor","creative","interesting","surprising","unique","extreme","skill","skills","performance","performer","performers","street","art","artistic","chain","moving","movement"}
def topic_keywords(search_queries):
 queries=list(search_queries or [])
 if not queries:return []
 groups=[]
 for q in queries:
  words=[w for w in re.findall(r"[a-z]{3,}",q.lower()) if w not in STOP]
  if words:groups.append(words)
 return groups
def topic_metadata_match(tags,queries):
 """Require at least one distinctive term from EVERY query group that has terms.
 Does not imply the scene actually depicts the desired action."""
 groups=topic_keywords(queries)
 if not groups:return False
 words=set(re.findall(r"[a-z]{3,}",str(tags).lower()))
 return all(any(w in words or (w.endswith("s") and w[:-1] in words) or (w+"s" in words) for w in group) for group in groups)
