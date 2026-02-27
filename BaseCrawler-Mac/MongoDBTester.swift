//
//  MongoDBTester.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import Foundation
import MongoSwift

class MongoDBTester: DatabaseConnectionTester {
    func testConnection(
        host: String,
        port: Int,
        username: String,
        password: String,
        database: String,
        useSSL: Bool
    ) async -> ConnectionTestResult {
        // Validate inputs
        guard !host.isEmpty else {
            return .failure(.invalidConfiguration("Host cannot be empty"))
        }
        
        guard (1...65535).contains(port) else {
            return .failure(.invalidConfiguration("Invalid port number"))
        }
        
        // Build connection string
        var connectionString: String
        if !username.isEmpty {
            let encodedUsername = username.addingPercentEncoding(withAllowedCharacters: .urlUserAllowed) ?? username
            let encodedPassword = password.addingPercentEncoding(withAllowedCharacters: .urlPasswordAllowed) ?? password
            connectionString = "mongodb://\(encodedUsername):\(encodedPassword)@\(host):\(port)"
        } else {
            connectionString = "mongodb://\(host):\(port)"
        }
        
        // Add database name if specified
        if !database.isEmpty {
            connectionString += "/\(database)"
        }
        
        // Add SSL/TLS option
        if useSSL {
            connectionString += database.isEmpty ? "/?" : "?"
            connectionString += "tls=true"
        }
        
        // Add timeout parameters
        connectionString += connectionString.contains("?") ? "&" : "/?"
        connectionString += "serverSelectionTimeoutMS=10000&connectTimeoutMS=10000"
        
        do {
            // Create client
            let client = try MongoClient(connectionString)
            let session = try await client.startSession()
            defer { Task { try? await session.end() } }
            
            // Try to ping the database
            let adminDB = client.db("admin")
            _ = try await adminDB.runCommand(["ping": 1], using: session)
            
            // Close the client
            try await client.close()
            
            return .success
            
        } catch {
            let errorMsg = "\(error)"
            if errorMsg.contains("Authentication") || errorMsg.contains("auth") {
                return .failure(.authenticationFailed("Invalid credentials"))
            } else if errorMsg.contains("not found") {
                return .failure(.databaseNotFound(database))
            } else if errorMsg.contains("timeout") || errorMsg.contains("Timeout") {
                return .failure(.connectionTimeout)
            } else {
                return .failure(.networkError(errorMsg))
            }
        }
    }
}

