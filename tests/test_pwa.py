import json
import unittest

from app import create_app


class PwaTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, AUTH_ENABLED=False)
        self.client = self.app.test_client()

    def test_manifest_declares_installable_app_metadata(self):
        response = self.client.get("/static/manifest.webmanifest")
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        manifest = json.loads(response.get_data(as_text=True))
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["icons"][0]["sizes"], "512x512")

    def test_service_worker_is_public_and_scoped_to_the_application(self):
        response = self.client.get("/service-worker.js")
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/javascript")
        self.assertEqual(response.headers["Service-Worker-Allowed"], "/")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_service_worker_only_caches_static_assets(self):
        response = self.client.get("/service-worker.js")
        self.addCleanup(response.close)
        source = response.get_data(as_text=True)

        self.assertIn('url.pathname.startsWith("/static/")', source)
        self.assertIn("request.mode === \"navigate\"", source)
        self.assertIn("fetch(request).catch(() => caches.match(OFFLINE_PAGE))", source)


if __name__ == "__main__":
    unittest.main()
