// winid PID -> CGWindowID of that process's largest normal window (on screen first, else any: other Space, covered)
import CoreGraphics
let pid = Int(CommandLine.arguments[1])!
func best(_ opt: CGWindowListOption) -> Int {
    let list = CGWindowListCopyWindowInfo(opt, kCGNullWindowID) as! [[String: Any]]
    var b = (0, 0.0)
    for w in list where (w[kCGWindowOwnerPID as String] as? Int) == pid && (w[kCGWindowLayer as String] as? Int) == 0 {
        let r = w[kCGWindowBounds as String] as! [String: Double]
        let a = r["Width"]! * r["Height"]!
        if a > b.1 { b = (w[kCGWindowNumber as String] as! Int, a) }
    }
    return b.0
}
let id = best([.optionOnScreenOnly])
print(id != 0 ? id : best([.optionAll]))
