import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.analysis.documents import extract_unit, inspect_document
from medicine_agent.analysis.models import AnalysisError, AnalysisRequest, PackageClassification
from medicine_agent.analysis.service import DataAnalysisAgent
from medicine_agent.analysis.store import process_lock
from medicine_agent.bootstrap import create_facade
from medicine_agent.domain.ids import file_sha256
from medicine_agent.packages.io import validate_package_path


FIXTURES = Path(__file__).parent / "fixtures" / "t02p"


def agent(tmp_path):
    return DataAnalysisAgent(tmp_path / "work", tmp_path / "packages")


def submit(a, path, **kwargs):
    return a.submit(AnalysisRequest(paths=[str(path)], allowed_use="self-authored-test",
                                   mode="extractive", **kwargs))


def cli(*args, timeout=180):
    result = subprocess.run([sys.executable, "-m", "medicine_agent.cli", "analyze", *map(str, args)],
                            capture_output=True, encoding="utf8", timeout=timeout)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_real_formats_and_locations():
    native = extract_unit(FIXTURES / "mixed.pdf", 1)
    assert native.method == "pdf-text"
    assert native.blocks[0].position.page == 1
    assert native.blocks[0].position.region
    scanned = extract_unit(FIXTURES / "mixed.pdf", 2)
    assert scanned.method == "ocr"
    text = "".join(b.text for b in scanned.blocks)
    assert "保留原文和来源" in text
    assert "数据分析完成后保存处理进度" in text
    assert scanned.blocks[0].position.render_scale == 2
    assert scanned.blocks[0].position.page == 2
    for name in ("scan.png", "scan.jpg"):
        image = extract_unit(FIXTURES / name, 1)
        assert "保留原文和来源" in "".join(b.text for b in image.blocks)
        assert image.blocks[0].confidence > .8
    _, count = inspect_document(FIXTURES / "sample.docx")
    units = [extract_unit(FIXTURES / "sample.docx", i) for i in range(1, count + 1)]
    assert any("cell" in (b.position.structure_path or "") for u in units for b in u.blocks)
    assert any(u.method == "ocr" for u in units)
    assert all(b.position.page is None for u in units for b in u.blocks)


def test_text_formats_and_mismatch(tmp_path):
    for suffix in (".txt", ".md"):
        p = tmp_path / ("text" + suffix)
        p.write_text("原文\n第二行", encoding="utf-8-sig")
        unit = extract_unit(p, 2)
        assert unit.blocks[0].text == "第二行"
        assert unit.blocks[0].position.structure_path == "line/2"
    fake = tmp_path / "renamed.txt"
    fake.write_bytes((FIXTURES / "mixed.pdf").read_bytes())
    with pytest.raises(AnalysisError, match="Content is pdf"):
        inspect_document(fake)
    p = tmp_path / "unknown.bin"
    p.write_bytes(b"unknown")
    with pytest.raises(AnalysisError):
        inspect_document(p)


def test_resume_does_not_repeat_extraction_and_keeps_parent_identity(tmp_path):
    a = agent(tmp_path)
    p = tmp_path / "source.txt"
    p.write_text("第一行\n第二行\n第三行", encoding="utf8")
    job = submit(a, p)
    parent, child = job["task_id"], job["children"][0]["task_id"]
    a.run(parent, max_units=1)
    paused = cli("run", parent, "--workspace", a.store.root, "--stop-after-extraction")
    assert paused["children"][0]["extracted"] == 2
    assert paused["children"][0]["analyzed"] == 1
    before = len([r for r in a.store.calls(child) if r["skill_id"] == "document-extraction"])
    finished = cli("run", parent, "--workspace", a.store.root)
    assert finished["status"] == "completed"
    assert finished["children"][0]["parent_task_id"] == parent
    after = len([r for r in a.store.calls(child) if r["skill_id"] == "document-extraction"])
    assert after - before == 1
    assert cli("run", parent, "--workspace", a.store.root)["status"] == "completed"


def test_revision_and_portable_folder_without_input_or_workspace(tmp_path):
    a = agent(tmp_path)
    source = tmp_path / "source.txt"
    source.write_text("第一段知识\n第二段知识", encoding="utf8")
    categories = PackageClassification(subjects=["中医内科学", "胸痹"], material_types=["textbook"],
        medical_profiles=["common", "tcm"], knowledge_layers=["general_pathomechanism"])
    job = submit(a, source, units=[1], classification=categories);v1 = a.run(job["task_id"])
    assert v1["status"] == "completed", v1
    relative1 = v1["children"][0]["package_path"]
    job2 = submit(a, source, parent_package=relative1)
    v2 = a.run(job2["task_id"])
    assert v2["status"] == "completed", v2
    selected = a.catalog.selected()
    assert selected[0]["revision"]["sequence"] == 2
    assert selected[0]["revision"]["changes"]["added_units"] == [2]
    second = tmp_path / "second.md"; second.write_text("其他资料知识", encoding="utf8")
    assert a.run(submit(a, second)["task_id"])["status"] == "completed"
    moved = tmp_path / "另一台电脑" / "知识包"
    shutil.copytree(a.catalog.root, moved)
    # Make original inputs and task workspace unavailable; copied packages stand alone.
    source.unlink();second.unlink()
    a.store.root.rename(tmp_path / "unavailable-workspace")
    catalog = PackageCatalog(moved)
    assert len(catalog.selected()) == 2
    result = catalog.query(create_facade(), text="知识")
    assert all(p["matches"] and p["evidence"] for p in result["packages"])
    filtered = catalog.query(create_facade(), text="知识", subject="中医内科学", material_type="textbook")
    assert len(filtered["packages"]) == 1
    assert filtered["packages"][0]["package"]["classification"]["subjects"] == ["中医内科学", "胸痹"]
    assert filtered["packages"][0]["package"]["classification"]["status"] == "declared"
    assert validate_package_path(moved / relative1).valid
    assert result["consultation_available"] is False
    catalog.select(relative1)
    assert next(i for i in catalog.selected() if i["family"] == selected[0]["family"])["revision"]["sequence"] == 1


def test_corrupt_checkpoint_source_runtime_and_lock(tmp_path):
    a = agent(tmp_path)
    p = tmp_path / "source.txt";p.write_text("原文\n后续", encoding="utf8")
    job = submit(a, p);parent=job["task_id"];child=job["children"][0]["task_id"]
    a.run(parent, max_units=1)
    with a.store.connect() as db:
        db.execute("UPDATE units SET extraction='broken' WHERE task=? AND ordinal=1", (child,))
    assert a.run(parent)["status"] == "completed"
    other = submit(a, p)
    child2 = other["children"][0]["task_id"]
    snapshot = a.store.task_dir(child2) / "input.txt"
    snapshot.write_text("changed", encoding="utf8")
    failed = a.run(other["task_id"])
    assert failed["children"][0]["errors"][0]["code"] == "SOURCE_CHANGED"
    assert a.run(other["task_id"], rebind=p)["children"][0]["errors"][0]["code"] == "PARENT_REVISION_REQUIRED"
    third = submit(a, p)
    c = third["children"][0]["task_id"]
    data = json.loads(a.store.get(c)["request"]);data["runtime"]["contract"] = "unknown"
    a.store.update(c, request=json.dumps(data))
    assert a.run(third["task_id"])["children"][0]["errors"][0]["code"] == "CHECKPOINT_VERSION_CONFLICT"
    a.store.update(c, request="{broken")
    assert a.run(third["task_id"])["children"][0]["errors"][0]["code"] == "CHECKPOINT_INVALID"
    with process_lock(a.store.task_dir(c) / "run.lock"):
        with pytest.raises(AnalysisError, match="Another process"):
            a.run(c)


def test_failed_parent_empty_and_model_requirements(tmp_path):
    a = agent(tmp_path)
    p = tmp_path / "empty.txt";p.write_text("\n\n", encoding="utf8")
    job=submit(a,p);assert a.run(job["task_id"])["status"] == "failed"
    assert a.catalog.scan() == []
    with pytest.raises(AnalysisError, match="real model"):
        a.submit(AnalysisRequest(paths=[str(p)], allowed_use="test"))
    with pytest.raises(AnalysisError):
        a.run("../../outside")
    with pytest.raises(AnalysisError):
        a._invoke(job["children"][0]["task_id"], "unknown-tool", {})


def test_tampered_package_and_path_escape_quarantined(tmp_path):
    a=agent(tmp_path);p=tmp_path/'a.txt';p.write_text('知识',encoding='utf8')
    job=submit(a,p);result=a.run(job['task_id']);relative=result['children'][0]['package_path']
    path=a.catalog.root/relative
    manifest=json.loads((path/'manifest.json').read_text('utf8'))
    manifest['files']['../outside.txt']='0000'
    (path/'manifest.json').write_text(json.dumps(manifest),encoding='utf8')
    report=validate_package_path(path)
    assert not report.valid
    assert any(i.code=='PACKAGE_PATH_INVALID' for i in report.issues)
    assert a.catalog.scan()[0]['state']=='quarantined'


def test_content_classification_is_only_a_candidate():
    from medicine_agent.analysis.classification import classify
    classified = classify("医案：主诉与现病史", {})
    assert classified["material_types"] == ["case_record"]
    assert classified["status"] == "candidate"
    assert classified["subjects"] == []
    assert classify("没有分类依据的文字", {})["status"] == "unclassified"


def test_top_level_agent_routes_goals_and_rejects_unimplemented_consultation(tmp_path):
    from medicine_agent.analysis.orchestrator import OrchestratorAgent
    top = OrchestratorAgent(tmp_path / "work", tmp_path / "packages")
    source = tmp_path / "note.txt"; source.write_text("测试知识", encoding="utf8")
    task = top.receive("analyze_files", {"paths": [str(source)], "allowed_use": "test", "mode": "extractive"})
    assert top.execute(task["task_id"])["status"] == "completed"
    assert top.receive("query_knowledge", {"text": "测试"})["packages"][0]["matches"]
    with pytest.raises(AnalysisError, match="no implemented handler"):
        top.receive("consultation", {"symptoms": "test"})


def test_abrupt_process_exit_after_real_ocr_commit(tmp_path):
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    book = tmp_path / "scanned-page-100.pdf"
    pdf = canvas.Canvas(str(book), pagesize=(750, 400))
    for page in range(1, 201):
        if page == 100:
            pdf.drawImage(ImageReader(str(FIXTURES / "scan.png")), 0, 50, width=750, height=300)
        else:
            pdf.drawString(40, 300, f"Self-authored page {page}")
        pdf.showPage()
    pdf.save()
    a = agent(tmp_path)
    job = submit(a, book, units=[100])
    child = job["children"][0]["task_id"]
    script = '''
import os,sys
from pathlib import Path
from medicine_agent.analysis.service import DataAnalysisAgent
a=DataAnalysisAgent(Path(sys.argv[1]));commit=a.store.commit_stage
def crash(task,ordinal,stage,payload):
    commit(task,ordinal,stage,payload)
    if stage=='extraction': os._exit(77)
a.store.commit_stage=crash
a.run(sys.argv[2])
'''
    crashed = subprocess.run([sys.executable, "-c", script, str(a.store.root), job["task_id"]],
                             capture_output=True, timeout=120)
    assert crashed.returncode == 77
    state = a.status(child)
    assert state["extracted"] == 1 and state["analyzed"] == 0
    saved = json.loads(a.store.rows(child)[0]["extraction"])
    assert saved["method"] == "ocr" and saved["blocks"][0]["position"]["page"] == 100
    result = cli("run", job["task_id"], "--workspace", a.store.root)
    assert result["status"] == "completed"
    assert len([r for r in a.store.calls(child) if r["skill_id"] == "document-extraction"]) == 1


def test_200_page_book_cross_process_resume(tmp_path):
    from reportlab.pdfgen import canvas
    book=tmp_path/'book.pdf'; c=canvas.Canvas(str(book))
    for i in range(1,201):
        c.drawString(40,700,f'Self-authored evidence page {i}.');c.showPage()
    c.save()
    a=agent(tmp_path);job=submit(a,book);parent=job['task_id'];child=job['children'][0]['task_id']
    # Each page uses an isolated native-parser process. Budget this integration
    # test separately from short CLI checks, including slower Windows hosts.
    first=cli('run',parent,'--workspace',a.store.root,'--max-units',100,timeout=600)
    assert first['children'][0]['analyzed']==100
    assert first['children'][0]['next_unit']==101
    before=a.store.calls(child)
    final=cli('run',parent,'--workspace',a.store.root,timeout=600)
    assert final['status']=='completed',final
    calls=a.store.calls(child)
    assert len([r for r in calls if r['skill_id']=='document-extraction'])==200
    assert all(r in calls for r in before)
    assert final['children'][0]['analyzed']==200
