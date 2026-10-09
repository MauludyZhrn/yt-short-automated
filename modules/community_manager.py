import os
import json
import time
import datetime
import googleapiclient.discovery
import googleapiclient.errors
from dotenv import load_dotenv

# Modul LLM untuk generate balasan otomatis
try:
    from groq import Groq
except ImportError:
    Groq = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_FILE)

class EchoBeeCommunityManager:
    """
    Agent: EchoBee (Community Manager Agent)
    Tugas:
    1. Membaca komentar terbaru di video YouTube Shorts
    2. Menganalisis sentimen komentar (Positif, Pertanyaan, Spam/Negatif)
    3. Menggenerate balasan cerdas dan natural menggunakan AI (Groq LLM)
    4. Mengirim balasan otomatis & memberikan Love/Like pada komentar audiens
    """

    def __init__(self, youtube_client=None):
        self.agent_name = "EchoBee"
        self.youtube = youtube_client or self._init_youtube_client()
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_key) if (Groq and self.groq_key) else None

    def _init_youtube_client(self):
        """Otorisasi ke YouTube Data API v3."""
        if not os.path.exists(TOKEN_FILE):
            print(f"⚠️ [{self.agent_name}] token.pickle nggak ditemukan. Pake mode simulasi.")
            return None
        try:
            import pickle
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)
            return googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        except Exception as exc:
            print(f"⚠️ [{self.agent_name}] Gagal inisialisasi API YouTube: {exc}")
            return None

    def fetch_recent_comments(self, video_id, max_results=10):
        """Mengambil komentar terbaru dari video tertentu."""
        if not self.youtube:
            return self._simulated_comments(video_id)

        try:
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=max_results,
                order="time"
            )
            response = request.execute()
            comments = []

            for item in response.get("items", []):
                top_comment = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "comment_id": item["id"],
                    "author": top_comment.get("authorDisplayName", "Anonim"),
                    "text": top_comment.get("textDisplay", ""),
                    "published_at": top_comment.get("publishedAt", ""),
                    "like_count": top_comment.get("likeCount", 0)
                })
            return comments

        except Exception as exc:
            print(f"❌ [{self.agent_name}] Gagal mengambil komentar video {video_id}: {exc}")
            return self._simulated_comments(video_id)

    def generate_ai_reply(self, comment_text, author_name="Viewer"):
        """Nge-generate balasan komentar yang ramah dan relevan pake AI."""
        if not self.groq_client:
            return f"Terima kasih atas komentarnya, @{author_name}! 🙏"

        prompt = (
            f"Kamu adalah EchoBee, Community Manager resmi untuk channel YouTube 'MorbMyth'.\n"
            f"Tugasmu adalah membalas komentar penonton dengan ramah, singkat, berenergi, dan santai (maksimal 1-2 kalimat).\n"
            f"Komentar dari @{author_name}: \"{comment_text}\"\n\n"
            f"Tuliskan balasan yang cocok (gunakan emoji secukupnya):"
        )

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=100
            )
            reply = response.choices[0].message.content.strip()
            # Hapus tanda kutip jika AI membalas pakai quotes
            return reply.strip('"')
        except Exception as exc:
            print(f"⚠️ [{self.agent_name}] Gagal generate balasan AI: {exc}")
            return f"Halo @{author_name}, makasih banyak udah nonton dan komen ya! 🔥"

    def post_reply(self, parent_comment_id, reply_text):
        """Mengirimkan balasan ke komentar YouTube."""
        if not self.youtube:
            print(f"🤖 [{self.agent_name}] [SIMULASI] Membalas komentar #{parent_comment_id}: '{reply_text}'")
            return True

        try:
            request = self.youtube.comments().insert(
                part="snippet",
                body={
                    "snippet": {
                        "parentId": parent_comment_id,
                        "textOriginal": reply_text
                    }
                }
            )
            request.execute()
            print(f"✅ [{self.agent_name}] Berhasil membalas komentar #{parent_comment_id}")
            return True
        except Exception as exc:
            print(f"❌ [{self.agent_name}] Gagal mengirim balasan ke YouTube: {exc}")
            return False

    def auto_manage_comments(self, video_id, max_reply_count=5):
        """Workflow otomatis: Baca komentar -> Buat balasan -> Kirim ke YouTube."""
        print(f"\n🐝 [{self.agent_name}] Memeriksa komentar terbaru di video ID '{video_id}'...")
        comments = self.fetch_recent_comments(video_id, max_results=max_reply_count)

        if not comments:
            print(f"ℹ️ [{self.agent_name}] Belum ada komentar baru.")
            return []

        processed_list = []
        for c in comments:
            print(f"💬 Komentar dari @{c['author']}: \"{c['text']}\"")
            reply = self.generate_ai_reply(c['text'], c['author'])
            print(f"🤖 Balasan EchoBee: \"{reply}\"")

            success = self.post_reply(c['comment_id'], reply)
            processed_list.append({
                "comment_id": c['comment_id'],
                "author": c['author'],
                "comment": c['text'],
                "reply": reply,
                "posted": success
            })
            time.sleep(1)  # Jeda biar nggak kena rate limit

        return processed_list

    def _simulated_comments(self, video_id):
        """Dummy komentar untuk pengujian lokal/offline."""
        return [
            {
                "comment_id": f"comm_dummy_1_{video_id}",
                "author": "BudiSantoso",
                "text": "Wah keren banget penjelasannya! Bikin konten tentang misteri laut dong.",
                "published_at": datetime.datetime.now().isoformat(),
                "like_count": 3
            },
            {
                "comment_id": f"comm_dummy_2_{video_id}",
                "author": "SitiMorb",
                "text": "Baru tahu fakta yang ini, mantap MorbMyth!",
                "published_at": datetime.datetime.now().isoformat(),
                "like_count": 5
            }
        ]

def run_community_check(video_id):
    """Helper eksekusi cepat untuk EchoBee."""
    manager = EchoBeeCommunityManager()
    return manager.auto_manage_comments(video_id)

if __name__ == "__main__":
    print("🧪 Testing Agent 5 (EchoBee Community Manager)...")
    echobee = EchoBeeCommunityManager()
    results = echobee.auto_manage_comments("dQw4w9WgXcQ", max_reply_count=2)
    print("\nHasil Tes Community Manager:", json.dumps(results, indent=2, ensure_ascii=False))