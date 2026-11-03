"""Test `tools/theo-goc.py` trên một repo git dựng tại chỗ, không chạm mạng hay kho thật.

    python tests/theo-goc/test_theo_goc.py

Phủ: lần đầu dựng gói 1.0.0 kèm mục danh mục; repo gốc không đổi thì không ra bản; đổi chữ thì
lên bản vá và không cần duyệt; đổi script thì lên bản vá và cần duyệt (lượt --khong-ma để lại nó);
commit chỉ đụng phần ngoài
skill thì không ra bản; liên kết mềm hay tên nhạy cảm thì từ chối và gói đứng yên; skill dạng tệp `.md`
phẳng (`phang`) chép nguyên văn thành `<tên>/SKILL.md`. Gói agent (`den: agents`): thân giữ nguyên byte,
phần đầu thêm khoá Vanhanh, bảng dịch, và gói lẻ (`tach`) thêm, lên bản, rời danh mục theo repo gốc.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


def _nap():
    spec = importlib.util.spec_from_file_location("theo_goc", GOC / "tools" / "theo-goc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


class TheoGoc(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tg-test-"))
        self.up = self.tmp / "up" / "tac-gia" / "kho-skill.git"
        (self.up / "skills" / "viet-thu").mkdir(parents=True)
        (self.up / "skills" / "viet-thu" / "SKILL.md").write_text(
            "---\nname: viet-thu\ndescription: Viết thư\n---\nThân skill.\n", encoding="utf-8")
        (self.up / "skills" / "viet-thu" / "chay.sh").write_text("echo 1\n", encoding="utf-8")
        (self.up / "README.md").write_text("repo\n", encoding="utf-8")
        (self.up / "LICENSE").write_text("MIT\n", encoding="utf-8")
        git(self.up, "init", "-q", "-b", "main")
        self.commit("đầu")

        self.kho = self.tmp / "kho"
        for d in ("theo-goc", "packs", "dist"):
            (self.kho / d).mkdir(parents=True)
        (self.kho / "index.json").write_text(json.dumps(
            {"format": "vanhanh-pack-index", "format_version": 1, "updated": "", "packs": []}), encoding="utf-8")
        (self.kho / "theo-goc" / "vanhanh.thu.json").write_text(json.dumps({
            "repo": "tac-gia/kho-skill", "ref": "main",
            "chep": [{"tu": "skills", "den": "skills"}],
            "goi": {"name": {"vi": "Thư", "en": "Letters"}, "description": {"vi": "a", "en": "a"},
                    "author": "Tác giả", "category": "van-phong",
                    "category_label": {"vi": "Văn phòng", "en": "Office"}, "license": "MIT"}}),
            encoding="utf-8")

        self.tg = _nap()
        self.tg.CAU_HINH = self.kho / "theo-goc"
        self.tg.GOI = self.kho / "packs"
        self.tg.INDEX = self.kho / "index.json"
        self.tg.DIST = self.kho / "dist"
        self.tg.GIT_GOC = (self.tmp / "up").as_uri() + "/"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def commit(self, msg):
        git(self.up, "add", "-A")
        git(self.up, "commit", "-q", "-m", msg)

    def muc(self):
        d = json.loads((self.kho / "index.json").read_text(encoding="utf-8"))
        return next(x for x in d["packs"] if x["id"] == "vanhanh.thu")

    def dong_bo(self):
        return self.tg.dong_bo("vanhanh.thu", hom_nay="2026-10-28")

    def test_lan_dau_dung_goi(self):
        kq = self.dong_bo()
        self.assertTrue(kq["doi"])
        m = self.muc()
        self.assertEqual(m["version"], "1.0.0")
        self.assertEqual(m["upstream"]["repo"], "tac-gia/kho-skill")
        self.assertEqual(len(m["upstream"]["commit"]), 40)
        self.assertEqual(m["provides"]["skills"], ["viet-thu"])
        goi = self.kho / "packs" / "vanhanh.thu"
        self.assertEqual((goi / "skills" / "viet-thu" / "SKILL.md").read_bytes(),
                         (self.up / "skills" / "viet-thu" / "SKILL.md").read_bytes(), "phải chép nguyên văn")
        self.assertTrue((goi / "docs" / "LICENSE-goc.txt").is_file())
        with zipfile.ZipFile(self.kho / m["download"]["url"]) as z:
            self.assertIn("skills/viet-thu/SKILL.md", z.namelist())
            self.assertIn("vanhanh-pack.yaml", z.namelist())

    def test_khong_doi_thi_khong_ra_ban(self):
        self.dong_bo()
        self.assertFalse(self.dong_bo()["doi"])
        (self.up / "README.md").write_text("repo khác\n", encoding="utf-8")
        self.commit("chỉ đổi README")
        self.assertFalse(self.dong_bo()["doi"], "commit ngoài phần skill không ra bản mới")
        self.assertEqual(self.muc()["version"], "1.0.0")

    def test_doi_chu_va_doi_ma(self):
        self.dong_bo()
        (self.up / "skills" / "viet-thu" / "SKILL.md").write_text(
            "---\nname: viet-thu\ndescription: Viết thư\n---\nThân mới.\n", encoding="utf-8")
        self.commit("sửa chữ")
        kq = self.dong_bo()
        self.assertTrue(kq["doi"])
        self.assertFalse(kq["can_duyet"], "chỉ đổi chữ thì không cần duyệt")
        self.assertEqual(self.muc()["version"], "1.0.1")
        (self.up / "skills" / "viet-thu" / "chay.sh").write_text("echo 2\n", encoding="utf-8")
        self.commit("sửa script")
        kq = self.dong_bo()
        self.assertTrue(kq["can_duyet"], "đổi script thì phải chờ duyệt")
        self.assertEqual(kq["tep_ma"], ["skills/viet-thu/chay.sh"])
        self.assertEqual(self.muc()["version"], "1.0.2")

    def test_khong_ma_de_lai_goi_can_duyet(self):
        self.dong_bo()
        (self.up / "skills" / "viet-thu" / "chay.sh").write_text("echo 3\n", encoding="utf-8")
        self.commit("sửa script")
        kq = self.tg.dong_bo("vanhanh.thu", hom_nay="2026-10-28", bo_qua_ma=True)
        self.assertTrue(kq["doi"] and kq["can_duyet"] and not kq["ghi"])
        self.assertEqual(self.muc()["version"], "1.0.0", "lượt --khong-ma không ghi gói có tệp mã đổi")
        self.assertEqual((self.kho / "packs" / "vanhanh.thu" / "skills" / "viet-thu" / "chay.sh").read_text(), "echo 1\n")

    def test_tu_choi_lien_ket_mem_va_ten_nhay_cam(self):
        self.dong_bo()
        for ten, tao in (("lien-ket", lambda p: os.symlink("/etc/passwd", p)),
                         (".env", lambda p: p.write_text("KEY=1\n"))):
            p = self.up / "skills" / "viet-thu" / ten
            tao(p)
            self.commit("thêm " + ten)
            with self.assertRaises(self.tg.LoiDongBo):
                self.dong_bo()
            self.assertEqual(self.muc()["version"], "1.0.0", "lỗi thì gói đứng yên ở bản cũ")
            p.unlink()
            self.commit("bỏ " + ten)

    def cau_hinh(self, chep):
        p = self.kho / "theo-goc" / "vanhanh.thu.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        c["chep"] = chep
        p.write_text(json.dumps(c), encoding="utf-8")

    def test_chi_bo_doi_ten(self):
        for ten in ("noi-bo", "ban-quyen"):
            (self.up / "skills" / ten).mkdir()
            (self.up / "skills" / ten / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        self.commit("thêm skill nội bộ")
        self.cau_hinh([{"tu": "skills", "den": "skills", "bo": ["noi-bo", "ban-quyen"],
                        "doi_ten": {"viet-thu": "tg-viet-thu"}}])
        self.dong_bo()
        goi = self.kho / "packs" / "vanhanh.thu" / "skills"
        self.assertEqual(sorted(p.name for p in goi.iterdir()), ["tg-viet-thu"])
        self.assertEqual((goi / "tg-viet-thu" / "SKILL.md").read_bytes(),
                         (self.up / "skills" / "viet-thu" / "SKILL.md").read_bytes(), "đổi tên thư mục, nội dung giữ nguyên")
        self.assertEqual(self.muc()["provides"]["skills"], ["tg-viet-thu"])
        self.cau_hinh([{"tu": "skills", "den": "skills", "chi": ["ban-quyen"]}])
        self.dong_bo()
        self.assertEqual(sorted(p.name for p in goi.iterdir()), ["ban-quyen"])
        self.cau_hinh([{"tu": "skills", "den": "skills", "chi": ["khong-co"]}])
        with self.assertRaises(self.tg.LoiDongBo):
            self.dong_bo()

    def test_skill_o_goc_repo(self):
        (self.up / "SKILL.md").write_text("---\nname: goc\n---\nThân.\n", encoding="utf-8")
        (self.up / "helpers").mkdir()
        (self.up / "helpers" / "a.py").write_text("print(1)\n", encoding="utf-8")
        (self.up / "tests").mkdir()
        (self.up / "tests" / "t.py").write_text("x\n", encoding="utf-8")
        (self.up / ".github").mkdir()
        (self.up / ".github" / "ci.yml").write_text("x\n", encoding="utf-8")
        self.commit("skill ở gốc")
        self.cau_hinh([{"tu": ".", "den": "skills", "ten": "goc", "bo_tep": ["tests", "skills"]}])
        self.dong_bo()
        goi = self.kho / "packs" / "vanhanh.thu" / "skills" / "goc"
        co = sorted(p.relative_to(goi).as_posix() for p in goi.rglob("*") if p.is_file())
        self.assertEqual(co, ["LICENSE", "README.md", "SKILL.md", "helpers/a.py"])
        self.assertEqual(self.muc()["tier"], "code", "có tệp .py thì gói là bậc code")

    def test_skill_phang(self):
        (self.up / "phang").mkdir()
        (self.up / "phang" / "fk-a.md").write_text("Làm A.\n", encoding="utf-8")
        (self.up / "phang" / "fk-b.md").write_text("# fk-b\nLàm B.\n", encoding="utf-8")
        (self.up / "phang" / "README.md").write_text("mục lục\n", encoding="utf-8")
        (self.up / "phang" / "mau").mkdir()
        (self.up / "phang" / "mau" / "x.json").write_text("{}\n", encoding="utf-8")
        self.commit("skill phẳng")
        self.cau_hinh([{"tu": "phang", "den": "skills", "phang": True, "bo": ["fk-b"]}])
        self.dong_bo()
        goi = self.kho / "packs" / "vanhanh.thu" / "skills"
        co = sorted(p.relative_to(goi).as_posix() for p in goi.rglob("*") if p.is_file())
        self.assertEqual(co, ["fk-a/SKILL.md"], "README và thư mục con không phải skill")
        self.assertEqual((goi / "fk-a" / "SKILL.md").read_bytes(),
                         (self.up / "phang" / "fk-a.md").read_bytes(), "phải chép nguyên văn")
        self.assertEqual(self.muc()["provides"]["skills"], ["fk-a"])
        self.cau_hinh([{"tu": "phang", "den": "skills", "phang": True, "chi": ["fk-c"]}])
        with self.assertRaises(self.tg.LoiDongBo):
            self.dong_bo()

    def test_cau_hinh_sai_bi_tu_choi(self):
        p = self.kho / "theo-goc" / "vanhanh.thu.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        for sai in ({"repo": "khong-co-gach"}, {"ref": "a..b"}, {"chep": [{"tu": "../x", "den": "skills"}]},
                    {"chep": [{"tu": "skills", "den": "plugins"}]},
                    {"chep": [{"tu": "skills", "den": "skills", "bo_tep": ["../x"]}]},
                    {"chep": [{"tu": "skills", "den": "skills", "doi_ten": ["a"]}]},
                    {"chep": [{"tu": "skills", "den": "skills", "doi_ten": {"viet-thu": "Ten Sai"}}]},
                    {"chep": [{"tu": "skills", "den": "skills", "phang": "co"}]},
                    {"chep": [{"tu": ".", "den": "skills", "ten": "goc", "phang": True}]}):
            p.write_text(json.dumps(dict(c, **sai)), encoding="utf-8")
            with self.assertRaises(self.tg.LoiDongBo):
                self.dong_bo()


GACH = chr(0x2014)
THAN_A = "\n# Agent A\n\nThân gốc " + GACH + " giữ nguyên.\n"
THAN_B = "\nThân B.\n"


class TheoGocAgent(unittest.TestCase):
    """Gói agent (`den: agents`) và gói lẻ (`tach`), kiểu repo agency-agents."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tg-agent-"))
        self.up = self.tmp / "up" / "tac-gia" / "agents.git"
        (self.up / "engineering").mkdir(parents=True)
        (self.up / "game" / "unity").mkdir(parents=True)
        (self.up / "engineering" / "engineering-a.md").write_text(
            '---\nname: Agent A\ndescription: "Does A ' + GACH + ' well"\ncolor: blue\n---' + THAN_A, encoding="utf-8")
        (self.up / "game" / "unity" / "unity-b.md").write_text(
            "---\nname: Unity B\ndescription: Builds B\n  across two lines\ntools: Read, Write\nslug: goc-b\n---"
            + THAN_B, encoding="utf-8")
        (self.up / "engineering" / "README.md").write_text("mục lục\n", encoding="utf-8")
        (self.up / "game" / "README.md").write_text("mục lục\n", encoding="utf-8")
        (self.up / "LICENSE").write_text("MIT\n", encoding="utf-8")
        git(self.up, "init", "-q", "-b", "main")
        self.commit("đầu")

        self.kho = self.tmp / "kho"
        for d in ("theo-goc/dich", "packs", "dist"):
            (self.kho / d).mkdir(parents=True)
        (self.kho / "index.json").write_text(json.dumps(
            {"format": "vanhanh-pack-index", "format_version": 1, "updated": "",
             "packs": [{"id": "vanhanh.khac"}]}), encoding="utf-8")
        self.cau_hinh = {
            "repo": "tac-gia/agents", "ref": "main", "tien_to": "ag-", "tach": "vanhanh.ag.", "the": "Bộ AG",
            "nhom_kho": {"lap-trinh": {"vi": "Lập trình", "en": "Development"}, "game": {"vi": "Làm game", "en": "Games"}},
            "chep": [{"tu": "engineering", "den": "agents", "nhan": {"vi": "Kỹ sư", "en": "Engineering"},
                      "category": "lap-trinh"},
                     {"tu": "game", "den": "agents", "nhan": {"vi": "Game", "en": "Game"}, "category": "game"}],
            "goi": {"name": {"vi": "AG", "en": "AG"}, "description": {"vi": "a", "en": "a"}, "author": "Tác giả",
                    "category": "tro-ly-ai", "category_label": {"vi": "Trợ lý AI", "en": "AI"}, "license": "MIT"}}
        self.ghi_cau_hinh()
        (self.kho / "theo-goc" / "dich" / "vanhanh.ag.json").write_text(json.dumps(
            {"_doc": "x", "engineering-a": ["Trợ lý A", "Làm A thật tốt."]}), encoding="utf-8")

        self.tg = _nap()
        self.tg.CAU_HINH = self.kho / "theo-goc"
        self.tg.GOI = self.kho / "packs"
        self.tg.INDEX = self.kho / "index.json"
        self.tg.DIST = self.kho / "dist"
        self.tg.GIT_GOC = (self.tmp / "up").as_uri() + "/"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ghi_cau_hinh(self, **sua):
        (self.kho / "theo-goc" / "vanhanh.ag.json").write_text(json.dumps(dict(self.cau_hinh, **sua)), encoding="utf-8")

    def commit(self, msg):
        git(self.up, "add", "-A")
        git(self.up, "commit", "-q", "-m", msg)

    def dong_bo(self):
        return self.tg.dong_bo("vanhanh.ag", hom_nay="2026-10-29")

    def goi(self):
        return json.loads((self.kho / "index.json").read_text(encoding="utf-8"))["packs"]

    def muc(self, gid):
        return next((x for x in self.goi() if x["id"] == gid), None)

    def tep(self, *p):
        return (self.kho / "packs" / "vanhanh.ag" / "agents" / Path(*p)).read_text(encoding="utf-8")

    def test_goi_gop_va_goi_le(self):
        self.assertTrue(self.dong_bo()["so_tach"] == 2)
        g = self.muc("vanhanh.ag")
        self.assertEqual(g["kind"], "agent")
        self.assertEqual(g["provides"], {"agents": ["ag-engineering-a", "ag-unity-b"]}, "README không phải agent")
        self.assertIn("upstream", g)

        a = self.tep("ag-engineering-a.md")
        self.assertTrue(a.endswith("---" + THAN_A), "thân agent giữ nguyên từng byte")
        self.assertIn('\nname: "Trợ lý A"\n', a)
        self.assertIn('\nrole: "Làm A thật tốt."\n', a)
        self.assertIn('\ntags:\n- "Kỹ sư"\n- "Bộ AG"\ngroup: "Kỹ sư"\nten_goc: "Agent A"\n', a)
        self.assertIn("\ncolor: blue\n", a, "khoá gốc khác giữ nguyên dòng")
        self.assertEqual(a.count("\nname:"), 1, "tên gốc chuyển sang ten_goc, không trùng khoá")

        b = self.tep("ag-unity-b.md")
        self.assertIn('\nname: "Unity B"\n', b, "chưa có bản dịch thì dùng tên gốc")
        self.assertIn('\nrole: "Builds B across two lines"\n', b, "mô tả nhiều dòng gộp lại")
        self.assertIn("\ntools: Read, Write\n", b)
        self.assertIn("\nslug: ag-unity-b\n", b)
        self.assertNotIn("goc-b", b, "khoá trùng tên khoá của Vanhanh bị bỏ")

        goi = [x["id"] for x in self.goi()]
        self.assertEqual(goi, ["vanhanh.khac", "vanhanh.ag", "vanhanh.ag.engineering-a", "vanhanh.ag.unity-b"],
                         "gói lẻ nằm ngay sau gói gộp")
        la = self.muc("vanhanh.ag.engineering-a")
        self.assertNotIn("upstream", la, "gói lẻ không vào mục Đề xuất")
        self.assertEqual((la["kind"], la["thuoc_goi"], la["category"]), ("agent", "vanhanh.ag", "lap-trinh"))
        self.assertEqual(la["name"], {"vi": "Trợ lý A", "en": "Agent A"})
        self.assertEqual(la["description"]["en"], "Does A - well", "kho không phát hành gạch dài")
        self.assertEqual(self.muc("vanhanh.ag.unity-b")["category_label"], {"vi": "Làm game", "en": "Games"})
        with zipfile.ZipFile(self.kho / la["download"]["url"]) as z:
            self.assertEqual(z.read("agents/ag-engineering-a.md").decode("utf-8"), a, "cùng byte với gói gộp")
            self.assertIn("docs/LICENSE-goc.txt", z.namelist())
        self.assertNotIn(GACH, (self.kho / "index.json").read_text(encoding="utf-8"))

    def test_cap_nhat_va_bo_agent(self):
        self.dong_bo()
        self.assertFalse(self.dong_bo()["doi"], "không đổi gì thì không ra bản")
        (self.up / "engineering" / "engineering-a.md").write_text(
            "---\nname: Agent A\ndescription: Does A\n---\nThân mới.\n", encoding="utf-8")
        self.commit("sửa A")
        self.assertTrue(self.dong_bo()["doi"])
        self.assertEqual(self.muc("vanhanh.ag")["version"], "1.0.1")
        self.assertEqual(self.muc("vanhanh.ag.engineering-a")["version"], "1.0.1")
        self.assertEqual(self.muc("vanhanh.ag.unity-b")["version"], "1.0.0", "agent không đổi thì gói lẻ đứng yên")
        (self.up / "game" / "unity" / "unity-b.md").unlink()
        self.commit("bỏ B")
        self.dong_bo()
        self.assertIsNone(self.muc("vanhanh.ag.unity-b"), "repo gốc bỏ agent thì gói lẻ rời danh mục")
        self.assertFalse((self.kho / "packs" / "vanhanh.ag.unity-b").exists())

    def test_ban_dich_doi_thi_ra_ban(self):
        self.dong_bo()
        (self.kho / "theo-goc" / "dich" / "vanhanh.ag.json").write_text(json.dumps(
            {"engineering-a": ["Trợ lý A mới", "Mô tả mới."]}), encoding="utf-8")
        self.dong_bo()
        self.assertEqual(self.muc("vanhanh.ag.engineering-a")["name"]["vi"], "Trợ lý A mới")
        self.assertEqual(self.muc("vanhanh.ag.engineering-a")["version"], "1.0.1")

    def test_tu_lanh_goi_le_bi_xoa(self):
        self.dong_bo()
        shutil.rmtree(self.kho / "packs" / "vanhanh.ag.unity-b")
        kq = self.dong_bo()
        self.assertEqual(kq["so_tach"], 1, "gói gộp đứng yên vẫn dựng lại gói lẻ bị mất")
        self.assertTrue((self.kho / "packs" / "vanhanh.ag.unity-b" / "vanhanh-pack.yaml").is_file())

    def test_cau_hinh_agent_sai(self):
        for sua in ({"tien_to": "Ag_"}, {"tach": "vanhanh.ag"},
                    {"chep": [{"tu": "engineering", "den": "agents", "category": "lap-trinh"}]},
                    {"chep": [{"tu": "engineering", "den": "agents", "nhan": {"vi": "a", "en": "b"},
                               "category": "khong-khai"}]},
                    {"chep": [{"tu": "engineering", "den": "agents", "nhan": {"vi": "a", "en": "b"},
                               "category": "lap-trinh", "phang": True}]}):
            self.ghi_cau_hinh(**sua)
            with self.assertRaises(self.tg.LoiDongBo):
                self.dong_bo()

    def test_agent_khong_frontmatter_bi_tu_choi(self):
        (self.up / "engineering" / "engineering-c.md").write_text("Không có phần đầu.\n", encoding="utf-8")
        self.commit("agent hỏng")
        with self.assertRaises(self.tg.LoiDongBo):
            self.dong_bo()


if __name__ == "__main__":
    unittest.main()
