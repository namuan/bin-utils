import Foundation
import Vision
import Cocoa

import Foundation
import Vision
import Cocoa

func performOCR(on image: NSImage) {
    guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("Failed to convert NSImage to CGImage.")
        return
    }

    if #available(macOS 10.15, *) {
        let request = VNRecognizeTextRequest { (request, error) in
            if let results = request.results as? [VNRecognizedTextObservation] {
                for observation in results {
                    if let topCandidate = observation.topCandidates(1).first {
                        print("Recognized text: \(topCandidate.string)")
                    }
                }
            } else {
                print("No text recognized.")
            }
        }

        request.recognitionLevel = .accurate

        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        do {
            try handler.perform([request])
        } catch {
            print("Failed to perform OCR: \(error.localizedDescription)")
        }
    } else {
        print("VNRecognizeTextRequest is not available on this version of macOS.")
    }
}

// Main execution
if CommandLine.argc < 2 {
    print("Usage: mac-ocr <image_path>")
    exit(1)
}

let imagePath = CommandLine.arguments[1]
let imageURL = URL(fileURLWithPath: imagePath)

if let image = NSImage(contentsOf: imageURL) {
    performOCR(on: image)
} else {
    print("Failed to load image at path: \(imagePath)")
}
