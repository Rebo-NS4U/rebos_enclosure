// Compile with -fno-access-control to exercise Qt's private screen-selection path.
#include <QtGui/QGuiApplication>
#include <QtGui/QWindow>
#include <QtGui/QScreen>
#include <QtWaylandClient/private/qwaylandwindow_p.h>
#include <QtWaylandClient/private/qwaylandsurface_p.h>
#include <QtWaylandClient/private/qwaylandscreen_p.h>
#include <cassert>

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    QWindow window;
    window.create();
    auto *native = dynamic_cast<QtWaylandClient::QWaylandWindow *>(window.handle());
    assert(native && native->mSurface);
    auto *live = QGuiApplication::primaryScreen()->handle();
    auto &entered = native->mSurface->m_screens;
    const auto original = entered;
    entered = {reinterpret_cast<QtWaylandClient::QWaylandScreen *>(1), nullptr};
    assert(native->calculateScreenFromSurfaceEvents() == live);
    entered.append(static_cast<QtWaylandClient::QWaylandScreen *>(live));
    assert(native->calculateScreenFromSurfaceEvents() == live);
    entered.clear();
    assert(native->calculateScreenFromSurfaceEvents() == live);
    entered = original;
    qInfo("PASS: stale, null, live, and empty surface screen lists");
}
