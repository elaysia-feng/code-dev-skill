"""验证 MP、访问器豁免以及 Java 边界扫描的正反例和索引行为。"""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import check_comments


def load(name, filename):
    """加载带连字符的工具脚本，不启动其命令行入口。"""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


boundary = load("java_boundary_checker", "check-java-boundaries.py")
smell = load("abstraction_checker", "check-abstraction-smell.py")


class JavaBoundaryTests(unittest.TestCase):
    """验证有源码依据的诊断，不依赖外部服务或数据库。"""

    def codes(self, files):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, source in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding="utf-8")
            findings, _ = boundary.scan(root)
            return {item.code for item in findings}

    def java(self, source, path="src/main/java/app/services/Demo.java", extra=None):
        return self.codes({path: source, **(extra or {})})

    def test_simple_accessors_are_exempt(self):
        for method in ("public String getName() { return this.name; }",
                       "public void setName(String value) { this.name = value; }",
                       "public boolean isEnabled() { return enabled; }",
                       "public String getURL() { return URL; }"):
            with self.subTest(method=method):
                issues = check_comments.check_source(Path("Demo.java"), "class Demo {\n" + method + "\n}")
                self.assertNotIn("missing-doc", {item.code for item in issues})

    def test_business_getter_and_wrong_field_are_not_exempt(self):
        for method in ("public String getName() { audit(); return name; }",
                       "public String getName() { return account.load(); }",
                       "public String getName() { return password; }",
                       "public void setName(String value) { validate(value); this.name = value; }"):
            issues = check_comments.check_source(Path("Demo.java"), "class Demo {\n" + method + "\n}")
            self.assertIn("missing-doc", {item.code for item in issues})

    def test_documented_accessor_does_not_need_redundant_tags(self):
        source = "class Demo {\n/** 名称。 */\npublic String getName() { return name; }\n}"
        self.assertFalse({"missing-doc", "missing-param", "missing-return"} &
                         {item.code for item in check_comments.check_source(Path("Demo.java"), source)})

    def test_mp_proxy_and_spring_controller_are_not_abstraction_smells(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "UserMapper.java").write_text(
                "import com.baomidou.mybatisplus.core.mapper.BaseMapper;\n"
                "public interface UserMapper extends BaseMapper<User> {}", encoding="utf-8")
            (root / "UserController.java").write_text(
                "import org.springframework.web.bind.annotation.RestController;\n"
                "@RestController\npublic class UserController {\n"
                "public Object get() { return service.get(); }\n}", encoding="utf-8")
            self.assertEqual(smell.find_single_impl_interfaces(root), [])
            self.assertEqual(smell.find_pass_through_methods(root), [])

    def test_mapper_suffix_and_controller_name_alone_do_not_exempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "FakeMapper.java").write_text("public interface FakeMapper {}", encoding="utf-8")
            (root / "FakeController.java").write_text(
                "public class FakeController {\npublic Object get() { return delegate.get(); }\n}", encoding="utf-8")
            self.assertEqual(len(smell.find_single_impl_interfaces(root)), 1)
            self.assertEqual(len(smell.find_pass_through_methods(root)), 1)

    def test_transactional_forwarder_keeps_framework_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Service.java").write_text(
                "import org.springframework.transaction.annotation.Transactional;\n"
                "class Service {\n@Transactional\npublic Object save() { return delegate.save(); }\n}", encoding="utf-8")
            self.assertEqual(smell.find_pass_through_methods(root), [])

    def test_direct_and_this_transaction_calls(self):
        for call in ("save();", "this.save();", "Runnable task = this::save;"):
            source = "class Demo {\npublic void run() { " + call + " }\n@Transactional\npublic void save() {}\n}"
            self.assertIn("transaction-self-invocation", self.java(source))

    def test_proxy_calls_and_text_do_not_count_as_self_calls(self):
        source = ('class Demo {\npublic void run() { other.save(); String s = "save()"; /* save(); */ }\n'
                  '@Transactional\npublic void save() {}\n}')
        self.assertNotIn("transaction-self-invocation", self.java(source))

    def test_outer_transaction_default_propagation_is_not_reported(self):
        source = "class Demo {\n@Transactional\npublic void run() { save(); }\n@Transactional\npublic void save() {}\n}"
        self.assertNotIn("transaction-self-invocation", self.java(source))

    def test_requires_new_is_not_hidden_by_outer_transaction(self):
        source = "class Demo {\n@Transactional\npublic void run() { save(); }\n@Transactional(propagation = Propagation.REQUIRES_NEW)\npublic void save() {}\n}"
        self.assertIn("transaction-self-invocation", self.java(source))

    def test_yaml_duplicate_default_and_key_ownership(self):
        source = '@ConfigurationProperties(prefix = "radar.ai")\nclass AiProperties {\nprivate int maxRetries = 2;\n}'
        yaml = "radar:\n  ai:\n    max-retries: 2\n"
        self.assertIn("duplicate-config-default", self.java(source, extra={"application.yml": yaml}))
        self.assertNotIn("duplicate-config-default", self.java(source, extra={"application.yml": yaml.replace("ai:", "mail:")}))

    def test_properties_default_and_no_java_fallback(self):
        source = '@ConfigurationProperties("radar.ai")\nclass AiProperties {\nprivate int maxRetries;\n}'
        self.assertNotIn("duplicate-config-default", self.java(source, extra={"application.properties": "radar.ai.max-retries=2"}))
        source = source.replace("maxRetries;", "maxRetries = 2;")
        self.assertIn("duplicate-config-default", self.java(source, extra={"application.properties": "radar.ai.max-retries=2"}))

    def test_commented_binding_is_not_configuration(self):
        source = 'import org.springframework.boot.context.properties.ConfigurationProperties;\n// @ConfigurationProperties("radar.ai")\nclass Demo { private int retries = 2; }'
        self.assertNotIn("duplicate-config-default", self.java(source, extra={"application.yml": "radar:\n  ai:\n    retries: 2\n"}))

    def test_hardcoded_parameters_and_protocol_constants(self):
        source = 'class Demo {\nprivate static final int RETRY_BACKOFF = 30;\nprivate static final int HTTP_STATUS_OK = 200;\n}'
        self.assertIn("hardcoded-tunable", self.java(source))
        self.assertNotIn("hardcoded-tunable", self.java(source.replace("RETRY_BACKOFF = 30", "COLUMN_TITLE = 3")))

    def test_runtime_duration_and_endpoint(self):
        source = 'package app.services.demo;\nclass Demo {\npublic void run() { client.uri("https://fixture.invalid"); sleep(Duration.ofSeconds(5)); }\n}'
        self.assertTrue({"hardcoded-endpoint", "hardcoded-runtime-duration"}.issubset(self.java(source)))
        self.assertNotIn("hardcoded-endpoint", self.java(source.replace('"https://fixture.invalid"', "properties.getUrl()")))

    def test_runtime_annotation_and_property_binding(self):
        source = 'class Demo {\n@Scheduled(fixedDelay = 1000)\npublic void run() {}\n}'
        self.assertIn("hardcoded-runtime-annotation", self.java(source))
        self.assertNotIn("hardcoded-runtime-annotation", self.java(source.replace('1000', '"${job.delay}"')))

    def test_test_fixture_parameters_are_not_production_hardcoding(self):
        source = 'class Demo { private static final int RETRY_BACKOFF = 30; }'
        self.assertNotIn("hardcoded-tunable", self.java(source, "src/test/java/app/DemoTest.java"))

    def test_annotation_fallback_and_secret_redaction(self):
        source = 'class Demo {\n@Value("${password:do-not-print}")\nprivate String password;\n}'
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "Demo.java"
            file.write_text(source, encoding="utf-8")
            result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "check-java-boundaries.py"), directory, "--json"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 1)
            self.assertIn("annotation-config-default", result.stdout)
            self.assertNotIn("do-not-print", result.stdout + result.stderr)

    def test_unused_integration_and_business_bypass(self):
        files = {"src/main/java/app/integration/zotero/ZoteroClient.java": "public interface ZoteroClient {}",
                 "src/main/java/app/integration/zotero/impl/ZoteroClientImpl.java": "class ZoteroClientImpl implements ZoteroClient {}",
                 "src/main/java/app/services/zotero/Service.java": "package app.services.zotero;\nclass Service { private WebClient client; }"}
        self.assertTrue({"integration-not-wired", "integration-bypass"}.issubset(self.codes(files)))
        files["src/test/java/app/ClientTest.java"] = "class ClientTest { private ZoteroClient client; }"
        self.assertIn("integration-not-wired", self.codes(files))
        files["src/main/java/app/services/zotero/Service.java"] = "class Service { private ZoteroClient client; }"
        self.assertNotIn("integration-not-wired", self.codes(files))

    def test_replacement_character_java_sql_yaml_and_comment_checker(self):
        for suffix in (".java", ".sql", ".yml"):
            self.assertIn("replacement-character", self.codes({"sample" + suffix: "// 原文\ufffd"}))
        issues = check_comments.check_source(Path("Demo.java"), "// 原文\ufffd\nclass Demo {}")
        self.assertIn("replacement-character", {item.code for item in issues})
        self.assertNotIn("replacement-character", self.codes({"Demo.java": 'class Demo { String value = "\\uFFFD"; }'}))

    def test_non_utf8_and_unmatched_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.java"
            path.write_bytes(b"\xff")
            findings, _ = boundary.scan(Path(directory))
            self.assertEqual(findings[0].code, "read-error")
            result = subprocess.run([sys.executable, str(SCRIPTS / "check-java-boundaries.py"), str(path.parent / "missing")], capture_output=True)
            self.assertEqual(result.returncode, 2)

    def test_staged_uses_index_and_retains_unchanged_config_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                subprocess.run(["git", "-C", directory, *args], check=True, capture_output=True)
            git("init", "-q")
            java = root / "AiProperties.java"
            java.write_text('@ConfigurationProperties("radar.ai")\nclass AiProperties {\nprivate int retries;\n}', encoding="utf-8")
            (root / "application.yml").write_text("radar:\n  ai:\n    retries: 2\n", encoding="utf-8")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
            java.write_text(java.read_text(encoding="utf-8").replace("retries;", "retries = 2;"), encoding="utf-8")
            git("add", "AiProperties.java")
            java.write_text("class Clean {}", encoding="utf-8")
            findings, count = boundary.staged_scan(root)
            self.assertEqual(count, 1)
            self.assertEqual({item.code for item in findings}, {"duplicate-config-default"})
            git("reset", "-q", "HEAD")
            self.assertEqual(boundary.staged_scan(root), ([], 0))

    def test_hook_blocks_sql_corruption_and_strict_runtime_warning(self):
        bash = os.environ.get("READABILITY_BASH", "bash")
        for source, filename, strict, expected in (
                ("-- 原文\ufffd", "migration.sql", "0", 1),
                ("class Demo { private static final int RETRY_BACKOFF = 30; }", "Demo.java", "0", 0),
                ("class Demo { private static final int RETRY_BACKOFF = 30; }", "Demo.java", "1", 1)):
            with self.subTest(filename=filename, strict=strict), tempfile.TemporaryDirectory() as directory:
                subprocess.run(["git", "-C", directory, "init", "-q"], check=True, capture_output=True)
                (Path(directory) / filename).write_text(source, encoding="utf-8")
                subprocess.run(["git", "-C", directory, "add", "."], check=True, capture_output=True)
                environment = {**os.environ, "READABILITY_PYTHON": sys.executable,
                               "READABILITY_FAIL_ON": "none", "COMMENT_FAIL_ON": "error",
                               "READABILITY_FIRST_STRICT": strict}
                result = subprocess.run([bash, str(SCRIPTS / "pre-commit-check.sh")], cwd=directory,
                                        env=environment, capture_output=True)
                self.assertEqual(result.returncode, expected, result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
