//
//  SQLiteTester.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import Foundation
import SQLite3

class SQLiteTester: DatabaseConnectionTester {
    func testConnection(
        host: String,
        port: Int,
        username: String,
        password: String,
        database: String,
        useSSL: Bool
    ) async -> ConnectionTestResult {
        // For SQLite, the 'host' or 'database' field contains the file path
        let filePath = host.isEmpty ? database : host
        
        guard !filePath.isEmpty else {
            return .failure(.invalidConfiguration("File path cannot be empty"))
        }
        
        // Expand tilde and resolve path
        let expandedPath = (filePath as NSString).expandingTildeInPath
        
        // Check if file exists
        let fileManager = FileManager.default
        if !fileManager.fileExists(atPath: expandedPath) {
            return .failure(.databaseNotFound("File does not exist at: \(expandedPath)"))
        }
        
        // Check if file is readable
        guard fileManager.isReadableFile(atPath: expandedPath) else {
            return .failure(.authenticationFailed("File is not readable (check permissions)"))
        }
        
        // Try to open the database
        var db: OpaquePointer?
        let result = sqlite3_open_v2(
            expandedPath,
            &db,
            SQLITE_OPEN_READONLY,
            nil
        )
        
        defer {
            if db != nil {
                sqlite3_close(db)
            }
        }
        
        guard result == SQLITE_OK else {
            let errorMessage = String(cString: sqlite3_errmsg(db))
            return .failure(.unknownError("Failed to open SQLite database: \(errorMessage)"))
        }
        
        // Try to execute a simple query to verify it's a valid SQLite database
        var stmt: OpaquePointer?
        let query = "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1"
        
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_finalize(stmt)
            return .success
        } else {
            let errorMessage = String(cString: sqlite3_errmsg(db))
            return .failure(.unknownError("Not a valid SQLite database: \(errorMessage)"))
        }
    }
}
