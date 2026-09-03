import asyncio


def test_mcp_exposes_gated_services_without_generic_provider_mutations(tmp_path):
    from ai_dlc.mcp_server import make_server

    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    server = make_server(tmp_path)
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert {"work_finish", "work_publish", "doctor", "knowledge_append"} <= names
    assert not names & {"provider_invoke", "tracker_complete", "set_status"}


def test_mcp_work_service_can_be_called_from_client_thread(tmp_path):
    import concurrent.futures

    from ai_dlc.mcp_server import make_server

    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    directory = tmp_path / ".ai-dlc/work"
    directory.mkdir(parents=True)
    (directory / "one.toml").write_text(
        'schema=1\nid="one"\ntitle="Task"\nscope="Scope"\nrequires_spec=false\nspec_reason="Small"\nacceptance=["Done"]\nreviewed=true\n'
    )
    server = make_server(tmp_path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(
            lambda: asyncio.run(server.call_tool("work_status", {"work_id": "one"}))
        ).result()
    assert "one" in str(result)
