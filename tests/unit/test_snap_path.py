# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
import pathlib

import snap


def test_path_joining():
    assert snap._Path("/foo") == snap._Path("/foo")
    assert snap._Path("/foo") / "bar" == snap._Path("/foo/bar")
    assert "/etc" / snap._Path("foo") / "bar" == snap._Path("/etc/foo/bar")
    assert "/etc" / snap._Path("foo") / "bar" / "baz" == snap._Path("/etc/foo/bar/baz")
    assert snap._Path("/etc", "foo", "bar", "baz") == snap._Path("/etc/foo/bar/baz")
    assert snap._Path("foo") == snap._Path("foo")
    assert "etc" / snap._Path("foo") / "bar" / "baz" == snap._Path("etc/foo/bar/baz")
    assert "/etc" / snap._Path("mysqlrouter") / "foo.conf" == snap._Path(
        "/etc/mysqlrouter/foo.conf"
    )


def test_outside_container():
    assert snap._Path("/foo") == pathlib.Path("/foo")
    assert snap._Path("/foo").relative_to_container == pathlib.PurePath("/foo")
    assert snap._Path("bar") == pathlib.Path("bar")
    assert snap._Path("bar").relative_to_container == pathlib.PurePath("bar")
    assert "/etc" / snap._Path("bar") == pathlib.Path("/etc/bar")
    assert ("/etc" / snap._Path("bar")).relative_to_container == pathlib.PurePath("/etc/bar")


def test_inside_container():
    assert snap._Path("/etc/mysqlrouter") == pathlib.Path(
        "/var/snap/charmed-mysql/current/etc/mysqlrouter"
    )
    assert snap._Path("/etc/mysqlrouter").relative_to_container == pathlib.PurePath(
        "/etc/mysqlrouter"
    )
    assert snap._Path("/etc") / "mysqlrouter" == pathlib.Path(
        "/var/snap/charmed-mysql/current/etc/mysqlrouter"
    )
    assert (snap._Path("/etc") / "mysqlrouter").relative_to_container == pathlib.PurePath(
        "/etc/mysqlrouter"
    )
    assert snap._Path("/etc/mysqlrouter/foo.conf") == pathlib.Path(
        "/var/snap/charmed-mysql/current/etc/mysqlrouter/foo.conf"
    )
    assert snap._Path("/etc/mysqlrouter/foo.conf").relative_to_container == pathlib.PurePath(
        "/etc/mysqlrouter/foo.conf"
    )
    assert "/etc" / snap._Path("mysqlrouter") / "foo.conf" == pathlib.Path(
        "/var/snap/charmed-mysql/current/etc/mysqlrouter/foo.conf"
    )
    assert (
        "/etc" / snap._Path("mysqlrouter") / "foo.conf"
    ).relative_to_container == pathlib.PurePath("/etc/mysqlrouter/foo.conf")

    assert snap._Path("/var/lib/mysqlrouter") == pathlib.Path(
        "/var/snap/charmed-mysql/current/var/lib/mysqlrouter"
    )
    assert snap._Path("/var/lib/mysqlrouter").relative_to_container == pathlib.PurePath(
        "/var/lib/mysqlrouter"
    )

    assert snap._Path("/run/mysqlrouter") == pathlib.Path(
        "/var/snap/charmed-mysql/common/run/mysqlrouter"
    )
    assert snap._Path("/run/mysqlrouter").relative_to_container == pathlib.PurePath(
        "/run/mysqlrouter"
    )

    assert snap._Path("/tmp") == pathlib.Path("/tmp/snap-private-tmp/snap.charmed-mysql/tmp")
    assert snap._Path("/tmp").relative_to_container == pathlib.PurePath("/tmp")
