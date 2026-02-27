//
//  Item.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import Foundation
import SwiftData

@Model
final class Item {
    var timestamp: Date
    
    init(timestamp: Date) {
        self.timestamp = timestamp
    }
}
