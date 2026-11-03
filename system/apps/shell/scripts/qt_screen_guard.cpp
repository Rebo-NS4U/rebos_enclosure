// Guard Qt's imported getter; internal Wayland calls bypass method overrides.
#include <QtGui/QGuiApplication>
#include <QtGui/QScreen>
#include <qpa/qplatformscreen.h>
#include <dlfcn.h>
#include <cstring>

QT_BEGIN_NAMESPACE
QScreen *QPlatformScreen::screen() const
{
    Dl_info caller{};
    dladdr(__builtin_return_address(0), &caller);
    if (caller.dli_sname && std::strcmp(caller.dli_sname,
            "_ZNK15QtWaylandClient14QWaylandWindow32calculateScreenFromSurfaceEventsEv") == 0) {
        // Compare addresses without dereferencing potentially stale outputs.
        for (auto *live : QGuiApplication::screens()) {
            if (live->handle() == this)
                return live;
        }
        return nullptr;
    }
    using Original = QScreen *(*)(const QPlatformScreen *);
    static auto original = reinterpret_cast<Original>(
        dlsym(RTLD_NEXT, "_ZNK15QPlatformScreen6screenEv"));
    return original(this);
}
QT_END_NAMESPACE
