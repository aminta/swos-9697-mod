// winid PID -> CGWindowID of that process's largest on-screen window
import CoreGraphics
let pid = Int(CommandLine.arguments[1])!
let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as! [[String: Any]]
var best = (0, 0.0)
for w in list where (w[kCGWindowOwnerPID as String] as? Int) == pid && (w[kCGWindowLayer as String] as? Int) == 0 {
    let b = w[kCGWindowBounds as String] as! [String: Double]
    let a = b["Width"]! * b["Height"]!
    if a > best.1 { best = (w[kCGWindowNumber as String] as! Int, a) }
}
print(best.0)
