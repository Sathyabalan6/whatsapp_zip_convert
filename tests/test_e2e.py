import unittest
import sys
import io
import json
import zipfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app

class TestE2E(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def create_mock_zip(self):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as wz:
            chat_log = (
                "28/07/2026, 14:30 - Alice: photo.jpg (file attached)\n"
                "This is a caption\n"
                "28/07/2026, 14:31 - Bob: audio.opus (file attached)\n"
            )
            wz.writestr("_chat.txt", chat_log)
            wz.writestr("photo.jpg", b"fake-image-bytes")
            wz.writestr("audio.opus", b"fake-audio-bytes")
        return zip_buffer.getvalue()

    def test_index_route(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

    def test_convert_stateless_flow(self):
        zip_bytes = self.create_mock_zip()
        data = {
            "zipfile": (io.BytesIO(zip_bytes), "export.zip")
        }
        res = self.client.post("/convert", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        
        res_data = json.loads(res.data)
        self.assertNotIn("conv_id", res_data)
        self.assertIn("manifest", res_data)
        self.assertIn("filename", res_data)
        self.assertIn("warnings", res_data)
        
        manifest = res_data["manifest"]
        self.assertEqual(manifest["chat_name"], "_chat")
        self.assertEqual(len(manifest["messages"]), 2)
        
        # Verify media content warning matches
        self.assertEqual(res_data["warnings"]["missing_media"], 0)

    def test_media_routes_not_found(self):
        # Media retrieval on the server must return 404 since media loading is handled 100% client-side
        res = self.client.get("/media/any-id/image/photo.jpg")
        self.assertEqual(res.status_code, 404)

        res2 = self.client.get("/export_media/any-id")
        self.assertEqual(res2.status_code, 404)

if __name__ == "__main__":
    unittest.main()
