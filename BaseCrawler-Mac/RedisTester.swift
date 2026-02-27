//
//  RedisTester.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import Foundation
import RediStack
import NIOCore
import NIOPosix

class RedisTester: DatabaseConnectionTester {
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
        
        let eventLoopGroup = MultiThreadedEventLoopGroup(numberOfThreads: 1)
        defer {
            try? eventLoopGroup.syncShutdownGracefully()
        }
        
        do {
            // Attempt connection with timeout
            return try await withThrowingTaskGroup(of: ConnectionTestResult.self) { group in
                group.addTask {
                    do {
                        // Create socket address
                        let address = try SocketAddress.makeAddressResolvingHost(host, port: port)
                        
                        // Connect to Redis
                        let conn = try await RedisConnection.make(
                            to: address,
                            on: eventLoopGroup.next()
                        ).get()
                        
                        // Authenticate if password provided
                        if !password.isEmpty {
                            let authArgs: [RESPValue] = [.init(bulk: password)]
                            _ = try await conn.send(command: "AUTH", with: authArgs).get()
                        }
                        
                        // Select database if specified
                        if !database.isEmpty, let dbNum = Int(database) {
                            let selectArgs: [RESPValue] = [.init(bulk: String(dbNum))]
                            _ = try await conn.send(command: "SELECT", with: selectArgs).get()
                        }
                        
                        // Send PING command to verify connection
                        _ = try await conn.ping().get()
                        
                        // Close the connection
                        conn.close()
                        
                        return .success
                    } catch {
                        let errorMsg = "\(error)"
                        if errorMsg.contains("WRONGPASS") || errorMsg.contains("NOAUTH") {
                            return .failure(.authenticationFailed("Invalid password"))
                        } else if errorMsg.contains("invalid DB index") || errorMsg.contains("ERR invalid DB") {
                            return .failure(.databaseNotFound(database))
                        } else if errorMsg.contains("Connection refused") || errorMsg.contains("Network") {
                            return .failure(.networkError("Could not connect to Redis server"))
                        } else {
                            return .failure(.networkError(errorMsg))
                        }
                    }
                }
                
                // Add timeout task
                group.addTask {
                    try await Task.sleep(for: .seconds(10))
                    return .failure(.connectionTimeout)
                }
                
                let result = try await group.next()!
                group.cancelAll()
                return result
            }
            
        } catch {
            return .failure(.networkError(error.localizedDescription))
        }
    }
}
